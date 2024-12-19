import math

from flask import render_template, request, redirect, session, jsonify
from flask_login import login_user, logout_user

import dao
import utils
from app import app, login
from app.models import UserRole, User


@app.route("/")
def index():
    cate_id = request.args.get('category_id')
    kw = request.args.get('kw')
    page = request.args.get('page', 1)
    prods = dao.load_products(cate_id=cate_id, kw=kw, page=int(page))

    page_size = app.config['PAGE_SIZE']
    total = dao.count_products()
    return render_template('index.html', products=prods, pages=math.ceil(total / page_size))


from flask import render_template, request, redirect, url_for, flash


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

    u = dao.auth_user(username=username, password=password, role=UserRole.ADMIN)
    if u:
        login_user(u)

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


@app.route("/api/carts", methods=['post'])
def add_to_cart():
    cart = session.get('cart')
    if not cart:
        cart = {}

    id = str(request.json.get('id'))
    name = request.json.get('name')
    price = request.json.get('price')

    if id in cart:
        cart[id]['quantity'] = cart[id]['quantity'] + 1
    else:
        cart[id] = {
            "id": id,
            "name": name,
            "price": price,
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
def pay():
    cart = session.get('cart')
    try:
        dao.add_to_cart(cart, request.json)
    except Exception as ex:
        return jsonify({'status': 500, 'message': str(ex)})
    else:
        return jsonify({'status': 200, 'message': 'successful'})


@app.route('/cart')
def cart_view():
    return render_template('cart.html')


@app.context_processor
def common_response_data():
    return {
        'categories': dao.load_categories(),
        'count_cart': utils.count_cart(session.get('cart'))
    }


if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
