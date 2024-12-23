import math

from flask import render_template, request, redirect, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user

import dao
import utils
from app import app, login
from app.models import UserRole, User, Product
from flask import render_template, request, redirect, url_for, flash


@app.route("/")
def index():
    kw = request.args.get('kw')
    cate_id = request.args.get('category_id')
    page = request.args.get('page', 1)

    prods = dao.load_products(kw=kw, category_id=cate_id, page=int(page))

    total = dao.count_products()

    return render_template('index.html', products=prods,
                           pages=math.ceil(total / app.config["PAGE_SIZE"]))


@app.route("/login", methods=['get', 'post'])
def login_process():
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')

        u = dao.auth_user(username=username, password=password)
        if u:
            login_user(u)

            next = request.args.get('next')
            return redirect('/' if next is None else next)

    return render_template('login.html')


@app.route("/login-admin", methods=['post'])
def login_admin_process():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu')
        return redirect('/admin')

    # Authenticate user with username and password
    u = dao.auth_user(username=username, password=password)

    if u:
        # Check if the user has the ADMIN or STAFF role
        if u and u.user_role in [UserRole.ADMIN, UserRole.STAFF]:
            login_user(u)
            return redirect('/admin')
        else:
            flash('Bạn không có quyền truy cập hệ thống')
            return redirect('/admin')
    else:
        flash('Tên đăng nhập hoặc mật khẩu không chính xác')
        return redirect('/admin')


@app.route("/logout")
def logout_process():
    logout_user()
    return redirect('/login')


@app.route("/register", methods=['get', 'post'])
def register_process():
    err_msg = None
    if request.method.__eq__('POST'):
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if password.__eq__(confirm):
            data = request.form.copy()
            del data['confirm']

            avatar = request.files.get('avatar')
            dao.add_user(avatar=avatar, **data)
            return redirect('/login')
        else:
            err_msg = 'Mật khẩu không khớp!'

    return render_template('register.html', err_msg=err_msg)


@app.context_processor
def common_context_params():
    return {
        'categories': dao.load_categories()
    }


@login.user_loader
def get_user_by_id(user_id):
    return dao.get_user_by_id(user_id)


@app.route("/api/carts", methods=['POST'])
def add_to_cart():
    cart = session.get('cart')
    if not cart:
        cart = {}

    product_id = str(request.json.get('id'))
    name = request.json.get('name')
    price = request.json.get('price')
    image = request.json.get('image')

    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        cart[product_id] = {
            "id": product_id,
            "name": name,
            "price": price,
            "image": image,
            "quantity": 1
        }

    session['cart'] = cart

    return jsonify(utils.count_cart(cart))


@app.route("/api/carts/<product_id>", methods=['PUT'])
def update_cart(product_id):
    quantity = request.json.get('quantity', 0)

    cart = session.get('cart')
    if cart and product_id in cart:
        cart[product_id]["quantity"] = int(quantity)

    session['cart'] = cart

    return jsonify(utils.count_cart(cart))


@app.route("/api/carts/<product_id>", methods=['delete'])
def delete_cart(product_id):
    cart = session.get('cart')
    if cart and product_id in cart:
        del cart[product_id]

    session['cart'] = cart

    return jsonify(utils.count_cart(cart))


@app.route("/api/pay", methods=['POST'])
@login_required
def pay():
    cart = session.get('cart')
    if not cart:
        return jsonify({'status': 400, 'msg': 'Giỏ hàng rỗng!'})

    try:
        dao.add_order(cart)
        session.pop('cart', None)  # Clear the cart after successful payment
        return jsonify({'status': 200, 'msg': 'Thanh toán thành công!'})
    except Exception as ex:
        return jsonify({'status': 500, 'msg': f'Lỗi: {str(ex)}'})


@app.route("/cart")
def cart_view():
    return render_template('cart.html')


@app.context_processor
def common_response_data():
    return {
        'categories': dao.load_categories(),
        'count_cart': utils.count_cart(session.get('cart')),
        'UserRole': UserRole
    }


@app.route("/products/<product_id>")
def details(product_id):
    comments = dao.load_comments(product_id)
    return render_template("details.html", product=dao.get_products_by_id(product_id), comments=comments)


@app.route("/api/products/<product_id>/comments", methods=['POST'])
@login_required
def add_comment(product_id):
    try:
        c = dao.add_comment(content=request.json.get('content'), product_id=product_id)
        # Format the datetime in the response
        formatted_date = c.created_date.strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({
            "status": 200,
            "comment": {
                "id": c.id,
                "content": c.content,
                "created_date": formatted_date,
                "user": {
                    "avatar": c.user.avatar,
                    "name": c.user.name
                }
            }
        })
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": str(e)
        })


@app.route('/clear-session')
def clear_session():
    session.clear()

    return redirect(url_for('index'))


##


@app.route("/api/import", methods=['POST'])
@login_required
def import_products_route():
    if current_user.user_role not in [UserRole.ADMIN, UserRole.STAFF]:
        return jsonify({
            "status": 403,
            "message": "You don't have permission to perform product imports"
        }), 403

    if not request.is_json:
        return jsonify({
            "status": 400,
            "message": "Request must be JSON"
        }), 400

    products_data = request.json.get('products')

    if not products_data or not isinstance(products_data, list):
        return jsonify({
            "status": 400,
            "message": "Request must include 'products' array"
        }), 400

    for item in products_data:
        if not isinstance(item, dict) or 'product_id' not in item or 'quantity' not in item:
            return jsonify({
                "status": 400,
                "message": "Each product must have 'product_id' and 'quantity'"
            }), 400

        if not isinstance(item['quantity'], int) or item['quantity'] <= 0:
            return jsonify({
                "status": 400,
                "message": "Quantity must be a positive integer"
            }), 400

    success, message = dao.import_products(current_user.id, products_data)

    if success:
        return jsonify({
            "status": 200,
            "message": message
        })
    else:
        return jsonify({
            "status": 400,
            "message": message
        }), 400


@app.route("/import", methods=['GET'])
@login_required
def import_interface():
    if current_user.user_role not in [UserRole.ADMIN, UserRole.STAFF]:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('index'))

    products = Product.query.all()
    return render_template('import_products.html', products=products)


if __name__ == '__main__':
    with app.app_context():
        from app import admin

        app.run(debug=True)
