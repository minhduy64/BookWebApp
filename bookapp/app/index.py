import math
from datetime import datetime, timedelta
from flask import render_template, request, redirect, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
import utils
from app import app, login, db
from app.models import UserRole, User, Product, PaymentMethod, OrderDetail, OrderStatus, Order
from flask import render_template, request, redirect, url_for, flash
import cloudinary.uploader
import hashlib
from app import dao

@app.route("/")
def index():
    kw = request.args.get('kw')
    cate_id = request.args.get('category_id')
    page = request.args.get('page', 1)

    prods = dao.load_products(kw=kw, category_id=cate_id, page=int(page))

    total = dao.count_products()

    return render_template('index.html', products=prods,
                           pages=math.ceil(total / app.config["PAGE_SIZE"]))


@app.route("/login", methods=['GET', 'POST'])
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

    # Xác thực người dùng bằng tên người dùng và mật khẩu
    u = dao.auth_user(username=username, password=password)

    if u:
        # Kiểm tra xem người dùng có vai trò quản trị hoặc nhân viên
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


@app.route("/register", methods=['GET', 'POST'])
def register_process():
    err_msg = None
    success_msg = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        # Kiểm tra xem mật khẩu và xác nhận có khớp không
        if password == confirm:
            try:
                # Kiểm tra xem tên người dùng đã tồn tại chưa
                if dao.is_username_taken(username):
                    err_msg = "Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác!"
                else:
                    # Chuẩn bị dữ liệu để đăng ký
                    data = request.form.copy()
                    del data['confirm']
                    avatar = request.files.get('avatar')

                    # Thêm người dùng vào cơ sở dữ liệu
                    dao.add_user(avatar=avatar, **data)

                    # Truy xuất người dùng mới đăng ký
                    user = {
                        "name": data.get('name'),
                        "username": username
                    }
                    success_msg = "Đăng ký tài khoản thành công!"
                    return render_template('register.html', success_msg=success_msg, user=user)
            except Exception as e:
                err_msg = f'Có lỗi xảy ra: {str(e)}'
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


@app.route("/cart")
def cart_view():
    return render_template('cart.html')


@app.route("/api/pay", methods=['POST'])
@login_required
def pay():
    cart = session.get('cart')
    if not cart:
        return jsonify({'status': 400, 'msg': 'Giỏ hàng rỗng!'})

    try:
        # Nhận phương thức thanh toán từ yêu cầu
        payment_data = request.get_json()
        payment_method = PaymentMethod[payment_data.get('paymentMethod', 'STORE_PICKUP')]
        delivery_address = payment_data.get('deliveryAddress')

        # Tạo đơn hàng mới
        order = Order(
            user_id=current_user.id,
            payment_method=payment_method,
            status=OrderStatus.PENDING,
            delivery_address=delivery_address if payment_method == PaymentMethod.ONLINE else None
        )
        db.session.add(order)

        # Thêm chi tiết đơn hàng
        for item in cart.values():
            detail = OrderDetail(
                order=order,
                product_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(detail)

            #Cập nhật kho sản phẩm
            product = Product.query.get(item['id'])
            if product:
                if product.quantity_in_stock < item['quantity']:
                    return jsonify({'status': 400, 'msg': f'Sản phẩm {product.name} không đủ số lượng!'})
                product.quantity_in_stock -= item['quantity']

        # Tính thời hạn lấy hàng cho các đơn hàng lấy tại cửa hàng
        if payment_method == PaymentMethod.STORE_PICKUP:
            order.pickup_deadline = datetime.now() + timedelta(hours=48)

        # Tính tổng số tiền
        order.calculate_total()

        db.session.commit()
        session.pop('cart', None)# Xóa giỏ hàng sau khi đặt hàng thành công

        return jsonify({
            'status': 200,
            'msg': 'Đặt hàng thành công!' +
                   (' Vui lòng đến nhận sách trong vòng 48 giờ.' if payment_method == PaymentMethod.STORE_PICKUP else
                    ' Đơn hàng sẽ được giao đến địa chỉ của bạn.')
        })

    except Exception as ex:
        db.session.rollback()
        return jsonify({'status': 500, 'msg': f'Lỗi: {str(ex)}'})


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
        # Định dạng ngày giờ trong phản hồi
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
            "message": "Bạn không có quyền thực hiện nhập sản phẩm"
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
                "message": "Số lượng phải là số nguyên dương"
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
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('index'))

    products = Product.query.all()
    return render_template('import_products.html', products=products)


@app.route("/api/import/new", methods=['POST'])
@login_required
def import_new_product():
    if current_user.user_role not in [UserRole.ADMIN, UserRole.STAFF]:
        return jsonify({
            "status": 403,
            "message": "Bạn không có quyền thực hiện nhập sản phẩm"
        }), 403

    if not request.is_json:
        return jsonify({
            "status": 400,
            "message": "Request must be JSON"
        }), 400

    data = request.json
    required_fields = ['name', 'author', 'price', 'category_id', 'quantity']

    # Validate required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "status": 400,
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    try:
        # Clean and validate quantity
        quantity = int(data['quantity'])
        if quantity <= 0:
            return jsonify({
                "status": 400,
                "message": "Số lượng phải là số nguyên dương"
            }), 400
        if quantity > 300:
            return jsonify({
                "status": 400,
                "message": "Số lượng không thể vượt quá 300"
            }), 400

        # Clean and validate price
        try:
            price = float(str(data['price']).replace(',', ''))
            if price <= 0:
                return jsonify({
                    "status": 400,
                    "message": "Giá phải là số dương"
                }), 400
        except ValueError:
            return jsonify({
                "status": 400,
                "message": "Định dạng giá không hợp lệ"
            }), 400

        # Tạo từ điển dữ liệu sản phẩm
        product_data = {
            'name': str(data['name']).strip(),
            'author': str(data['author']).strip(),
            'description': str(data.get('description', '')).strip(),
            'price': price,
            'image': data.get('image'),
            'active': bool(data.get('active', True)),
            'category_id': int(data['category_id'])
        }

        success, message = dao.import_product_with_details(
            staff_id=current_user.id,
            product_data=product_data,
            import_quantity=quantity
        )

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

    except ValueError as e:
        return jsonify({
            "status": 400,
            "message": f"Invalid data format: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({
            "status": 500,
            "message": f"Server error: {str(e)}"
        }), 500


@app.route("/orders")
@login_required
def order_history():
    return render_template('order_history.html')


@app.route("/profile", methods=['GET'])
@login_required
def profile():
    return render_template('profile.html')


@app.route("/profile/update", methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        try:
            # Cập nhật tên
            current_user.name = request.form.get('name')

            # Xử lý thay đổi mật khẩu nếu được cung cấp
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if current_password and new_password and confirm_password:
                # Xác minh mật khẩu hiện tại
                if current_user.password == hashlib.md5(current_password.strip().encode('utf-8')).hexdigest():
                    if new_password == confirm_password:
                        current_user.password = hashlib.md5(new_password.strip().encode('utf-8')).hexdigest()
                        flash('Cập nhật thông tin thành công')
                    else:
                        flash('Mật khẩu mới không khớp', 'error')
                else:
                    flash('Mật khẩu hiện tại không chính xác', 'error')

            db.session.commit()
            flash('Cập nhật thông tin thành công')

        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra: {str(e)}', 'error')

    return redirect(url_for('profile'))


@app.route("/profile/avatar", methods=['POST'])
@login_required
def update_avatar():
    if request.method == 'POST':
        try:
            avatar = request.files.get('avatar')
            if avatar:
                # Upload Cloudinary
                result = cloudinary.uploader.upload(avatar)
                current_user.avatar = result.get('secure_url')
                db.session.commit()
                flash('Cập nhật ảnh đại diện thành công')

        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra: {str(e)}', 'error')

    return redirect(url_for('profile'))


if __name__ == '__main__':
    with app.app_context():
        from app import admin

        app.run(debug=True)