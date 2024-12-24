import atexit
from datetime import datetime

from sqlalchemy import func, event

from app.models import Category, Product, User, Order, OrderDetail, Comment, ProductImport, ProductImportDetail, \
    OrderStatus, PaymentMethod
from app import app, db
import hashlib
import cloudinary.uploader
from flask_login import current_user
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler


def load_categories():
    return Category.query.order_by('id').all()


def load_products(kw=None, category_id=None, page=1):
    products = Product.query

    if kw:
        products = products.filter(Product.name.contains(kw))

    if category_id:
        products = products.filter(Product.category_id == category_id)

    page_size = app.config["PAGE_SIZE"]
    start = (page - 1) * page_size
    products = products.slice(start, start + page_size)

    return products.all()


def import_products(staff_id, products_data):
    # Kiểm tra tổng số lượng nhập khẩu tối thiểu
    total_import_quantity = sum(b['quantity'] for b in products_data)
    if total_import_quantity < 150:
        return False, "Số lượng nhập tối thiểu phải là 150"

    # Xác thực số lượng hiện tại của từng sản phẩm
    for product_data in products_data:
        product = product.query.get(product_data['product_id'])
        if not product:
            return False, f"Kông tìm thấy sản phẩm có id {product_data['product_id']}"

        # Kiểm tra xem số lượng sản phẩm hiện tại đã từ 300 trở lên chưa
        if product.quantity >= 300:
            return False, f"Không thể nhập sản phẩm '{product.title}' - số lượng hiện tại ({product.quantity}) đã 300 hoặc hơn"

        # Kiểm tra xem việc nhập có vượt quá 300 hay không
        new_quantity = product.quantity + product_data['quantity']
        if new_quantity > 300:
            return False, f"Cannot import {product_data['quantity']} units of '{product.title}' - would exceed 300 limit (current: {product.quantity})"


def count_products():
    return Product.query.count()


def auth_user(username, password, role=None):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

    u = User.query.filter(User.username.__eq__(username),
                          User.password.__eq__(password))

    if role:
        u = u.filter(User.user_role.__eq__(role))

    return u.first()


def get_user_by_id(user_id):
    return User.query.get(user_id)


def get_user_by_username(username):
    return User.query.get(username)


from flask import flash


def add_user(name, username, password, email, phone_number=None, avatar=None):
    # Kiểm tra xem tên người dùng có tồn tại không
    if is_username_taken(username):
        flash("Tên tài khoản đã tồn tại, hãy chọn tên tài khoản khác", "warning")
        return False, "Tên tài khoản đã tồn tại"

    # Kiểm tra xem email có tồn tại không
    if is_email_taken(email):
        flash("Email đã tồn tại, hãy sử dụng email khác", "warning")
        return False, "Email đã tồn tại"

    # Kiểm tra xem số điện thoại có tồn tại không
    if phone_number and is_phone_number_taken(phone_number):
        flash("Số điện thoại đã tồn tại, hãy sử dụng số điện thoại khác", "warning")
        return False, "Số điện thoại đã tồn tại"

    try:
        # Băm mật khẩu
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

        # Tạo đối tượng người dùng mới
        u = User(
            name=name,
            username=username,
            password=password,
            email=email,
            phone_number=phone_number
        )

        # Xử lý tải lên hình đại diện
        if avatar:
            res = cloudinary.uploader.upload(avatar)
            u.avatar = res.get('secure_url')

        # Lưu vào cơ sở dữ liệu
        db.session.add(u)
        db.session.commit()
        flash("Đăng ký tài khoản thành công", "success")
        return True, "Đăng ký tài khoản thành công"

    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi khi đăng ký: {str(e)}", "danger")
        return False, f"Lỗi khi đăng ký: {str(e)}"


def is_username_taken(username):
    return User.query.filter_by(username=username).first() is not None


def is_email_taken(email):
    return User.query.filter_by(email=email).first() is not None


def is_phone_number_taken(phone_number):
    return User.query.filter_by(phone_number=phone_number).first() is not None


def add_order(cart):
    if cart:
        r = Order(user_id=current_user.id)
        db.session.add(r)

        for c in cart.values():
            d = OrderDetail(
                quantity=c['quantity'],
                price=c['price'],
                product_id=c['id'],
                order=r
            )
            db.session.add(d)

        db.session.commit()


def revenue_stats(kw=None):
    total_revenue_query = db.session.query(func.sum(OrderDetail.price * OrderDetail.quantity)).scalar() or 1
    query = db.session.query(
        Product.id,
        Product.name,
        func.sum(OrderDetail.price * OrderDetail.quantity),
        func.sum(OrderDetail.quantity),
        (func.sum(OrderDetail.price * OrderDetail.quantity) / total_revenue_query * 100).label('proportion')
    ).join(OrderDetail, OrderDetail.product_id == Product.id)
    if kw:
        query = query.filter(Product.name.contains(kw))

    return query.group_by(Product.id).all()


def revenue_month_stats(time='month', year=datetime.now().year):
    total_revenue_query = db.session.query(func.sum(OrderDetail.price * OrderDetail.quantity)).scalar() or 1
    query = db.session.query(
        func.extract('month', Order.order_date),
        func.sum(OrderDetail.quantity * OrderDetail.price),
        func.sum(OrderDetail.quantity),
        (func.sum(OrderDetail.quantity * OrderDetail.price) / total_revenue_query * 100).label('proportion')
    ).join(OrderDetail, OrderDetail.order_id == Order.id) \
        .filter(func.extract('year', Order.order_date) == year) \
        .group_by(func.extract('month', Order.order_date))
    return query.all()


def stats_products():
    return (db.session.query(Category.id, Category.name, func.count(Product.id))
            .join(Product, Product.category_id.__eq__(Category.id), isouter=True)).group_by(Category.id).all()


def revenue_month_stats_by_category(time='month', year=datetime.now().year):
    total_revenue_query = db.session.query(func.sum(OrderDetail.price * OrderDetail.quantity)).scalar() or 1
    query = db.session.query(
        Category.name,
        func.extract('month', Order.order_date),
        func.sum(OrderDetail.price * OrderDetail.quantity),
        func.sum(OrderDetail.quantity),
        (func.sum(OrderDetail.price * OrderDetail.quantity) / total_revenue_query * 100).label('proportion')
    ).join(Product, Product.category_id == Category.id) \
        .join(OrderDetail, OrderDetail.product_id == Product.id) \
        .join(Order, Order.id == OrderDetail.order_id) \
        .filter(func.extract('year', Order.order_date) == year) \
        .group_by(Category.name, func.extract('month', Order.order_date)) \
        .order_by(Category.name, func.extract('month', Order.order_date))
    return query.all()


def get_products_by_id(id):
    return Product.query.get(id)


def load_comments(product_id):
    return Comment.query.filter(Comment.product_id.__eq__(product_id))


def add_comment(content, product_id):
    c = Comment(content=content,
                product_id=product_id,
                user=current_user,
                created_date=datetime.now())
    db.session.add(c)
    db.session.commit()
    return c


## ##
def import_products(staff_id, products_data):

    # Kiểm tra tổng số lượng nhập khẩu tối thiểu
    total_import_quantity = sum(product['quantity'] for product in products_data)
    if total_import_quantity < 150:
        return False, "Total import quantity must be at least 150 books"

    try:
        # Tạo biên lai nhập hàng trước
        import_receipt = ProductImport(
            staff_id=staff_id,
            total_quantity=total_import_quantity
        )
        db.session.add(import_receipt)

        # Xác thực và xử lý từng sản phẩm
        for product_data in products_data:
            product = Product.query.get(product_data['product_id'])
            if not product:
                db.session.rollback()
                return False, f"Product with ID {product_data['product_id']} not found"

            current_quantity = product.quantity_in_stock
            import_quantity = product_data['quantity']

            # Validate maximum quantity
            if current_quantity >= 300:
                db.session.rollback()
                return False, f"Cannot import '{product.name}' - current quantity ({current_quantity}) is already at maximum (300)"

            new_quantity = current_quantity + import_quantity
            if new_quantity > 300:
                db.session.rollback()
                return False, f"Cannot import {import_quantity} units of '{product.name}' - would exceed 300 limit (current: {current_quantity})"

            # Tạo chi tiết nhập
            detail = ProductImportDetail(
                import_receipt=import_receipt,
                product_id=product.id,
                quantity=import_quantity
            )
            db.session.add(detail)

            #Cập nhật kho sản phẩm
            product.quantity_in_stock = new_quantity

        # Tính tổng số lượng cho biên lai nhập khẩu
        import_receipt.calculate_total_quantity()

        db.session.commit()
        return True, "Import successful"

    except Exception as e:
        db.session.rollback()
        return False, f"Error during import: {str(e)}"


def import_product_with_details(staff_id, product_data, import_quantity):

    try:
        # Create new product
        product = Product(
            name=str(product_data['name']),
            author=str(product_data['author']),
            description=str(product_data.get('description', '')),
            price=float(product_data['price']),
            image=str(product_data.get('image', '')),
            active=bool(product_data.get('active', True)),
            category_id=int(product_data['category_id']),
            quantity_in_stock=0
        )

        db.session.add(product)
        db.session.flush()

        # Tạo biên lai nhập hàng
        import_receipt = ProductImport(
            staff_id=staff_id,
            total_quantity=import_quantity,
            notes=f"Initial import for product: {product.name}"
        )
        db.session.add(import_receipt)
        db.session.flush()

        # Tạo chi tiết nhập hàng
        detail = ProductImportDetail(
            import_id=import_receipt.id,
            product_id=product.id,
            quantity=import_quantity
        )
        db.session.add(detail)

        # Cập nhật trực tiếp kho sản phẩm
        product.quantity_in_stock = import_quantity

        db.session.commit()
        return True, "Product imported successfully"

    except ValueError as e:
        db.session.rollback()
        return False, f"Invalid data format: {str(e)}"
    except Exception as e:
        db.session.rollback()
        return False, f"Error during import: {str(e)}"


@event.listens_for(ProductImportDetail, 'after_insert')
def update_stock_after_import(mapper, connection, target):
    #Cập nhật kho sản phẩm sau khi chi tiết nhập mới được tạo"
    if target.product:
        target.product.quantity_in_stock += target.quantity


@event.listens_for(ProductImportDetail, 'before_delete')
def revert_stock_before_delete(mapper, connection, target):
    #Hoàn nguyên kho sản phẩm trước khi chi tiết nhập bị xóa
    if target.product:
        target.product.quantity_in_stock -= target.quantity


def cancel_expired_orders():
    with app.app_context():
        # Tìm tất cả các đơn đặt hàng nhận tại cửa hàng đang chờ xử lý đã quá thời hạn
        expired_orders = Order.query.filter(
            Order.status == OrderStatus.PENDING,
            Order.payment_method == PaymentMethod.STORE_PICKUP,
            Order.pickup_deadline < datetime.now()
        ).all()

        for order in expired_orders:
            # Trả sản phẩm về kho
            for detail in order.details:
                product = Product.query.get(detail.product_id)
                if product:
                    product.quantity_in_stock += detail.quantity

            # Cập nhật trạng thái đơn hàng
            order.status = OrderStatus.CANCELLED

        db.session.commit()


#Thiết lập lịch trình
scheduler = BackgroundScheduler()
scheduler.add_job(func=cancel_expired_orders, trigger="interval", hours=1)
scheduler.start()

# Tắt bộ lập lịch khi thoát ứng dụng
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
