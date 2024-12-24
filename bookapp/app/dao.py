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
    # Check minimum total import quantity
    total_import_quantity = sum(b['quantity'] for b in products_data)
    if total_import_quantity < 150:
        return False, "Minimum import quantity must be 150"

    # Validate each product's current quantity
    for product_data in products_data:
        product = product.query.get(product_data['product_id'])
        if not product:
            return False, f"product with id {product_data['product_id']} not found"

        # Check if current product quantity is already 300 or more
        if product.quantity >= 300:
            return False, f"Cannot import product '{product.title}' - current quantity ({product.quantity}) is already 300 or more"

        # Check if import would exceed 300 limit
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


def add_user(name, username, password, avatar=None):
    if is_username_taken(username):
        return False, "Tên tài khoản đã tồn tại, hãy chọn tên tài khoản khác"

    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = User(name=name, username=username, password=password)

    if avatar:
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get('secure_url')

    db.session.add(u)
    db.session.commit()
    return True, "Đăng ký tài khoản  thành công"


def is_username_taken(username):
    return User.query.filter_by(username=username).first() is not None


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
    """
    Import products with quantity validation and updates

    Args:
        staff_id: ID of the staff member performing the import
        products_data: List of dicts with product_id and quantity

    Returns:
        tuple: (success: bool, message: str)
    """
    # Check minimum total import quantity
    total_import_quantity = sum(product['quantity'] for product in products_data)
    if total_import_quantity < 150:
        return False, "Total import quantity must be at least 150 books"

    try:
        # Create import receipt first
        import_receipt = ProductImport(
            staff_id=staff_id,
            total_quantity=total_import_quantity
        )
        db.session.add(import_receipt)

        # Validate and process each product
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

            # Create import detail
            detail = ProductImportDetail(
                import_receipt=import_receipt,
                product_id=product.id,
                quantity=import_quantity
            )
            db.session.add(detail)

            # Update product stock
            product.quantity_in_stock = new_quantity

        # Calculate total quantity for the import receipt
        import_receipt.calculate_total_quantity()

        db.session.commit()
        return True, "Import successful"

    except Exception as e:
        db.session.rollback()
        return False, f"Error during import: {str(e)}"


def import_product_with_details(staff_id, product_data, import_quantity):
    """
    Import a new product or update existing one with import details
    """
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
            quantity_in_stock=0  # Will be updated through import detail
        )

        db.session.add(product)
        db.session.flush()  # Get product ID without committing

        # Create import receipt
        import_receipt = ProductImport(
            staff_id=staff_id,
            total_quantity=import_quantity,
            notes=f"Initial import for product: {product.name}"
        )
        db.session.add(import_receipt)
        db.session.flush()

        # Create import detail
        detail = ProductImportDetail(
            import_id=import_receipt.id,
            product_id=product.id,
            quantity=import_quantity
        )
        db.session.add(detail)

        # Update product stock directly
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
    """Update product stock after a new import detail is created"""
    if target.product:
        target.product.quantity_in_stock += target.quantity


@event.listens_for(ProductImportDetail, 'before_delete')
def revert_stock_before_delete(mapper, connection, target):
    """Revert product stock before an import detail is deleted"""
    if target.product:
        target.product.quantity_in_stock -= target.quantity


def cancel_expired_orders():
    with app.app_context():
        # Find all pending store pickup orders that are past their deadline
        expired_orders = Order.query.filter(
            Order.status == OrderStatus.PENDING,
            Order.payment_method == PaymentMethod.STORE_PICKUP,
            Order.pickup_deadline < datetime.now()
        ).all()

        for order in expired_orders:
            # Return products to inventory
            for detail in order.details:
                product = Product.query.get(detail.product_id)
                if product:
                    product.quantity_in_stock += detail.quantity

            # Update order status
            order.status = OrderStatus.CANCELLED

        db.session.commit()


# Set up the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=cancel_expired_orders, trigger="interval", hours=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
