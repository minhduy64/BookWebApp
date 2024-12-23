from datetime import datetime

from sqlalchemy import func

from app.models import Category, Product, User, Order, OrderDetail, Comment, ProductImport, ProductImportDetail
from app import app, db
import hashlib
import cloudinary.uploader
from flask_login import current_user


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
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())

    u = User(name=name, username=username, password=password)
    if avatar:
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get('secure_url')

    db.session.add(u)
    db.session.commit()


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

    total_import_quantity = sum(product['quantity'] for product in products_data)
    if total_import_quantity < 150:
        return False, "Total import quantity must be at least 150 books"


    for product_data in products_data:
        product = Product.query.get(product_data['product_id'])
        if not product:
            return False, f"Product with ID {product_data['product_id']} not found"

        current_quantity = product.quantity_in_stock
        import_quantity = product_data['quantity']


        if current_quantity >= 300:
            return False, f"Cannot import '{product.name}' - current quantity ({current_quantity}) is already at maximum (300)"


        if current_quantity + import_quantity > 300:
            allowed_import = 300 - current_quantity
            return False, f"Cannot import {import_quantity} units of '{product.name}' - would exceed 300 limit. Maximum allowed import: {allowed_import}"


    try:
        import_receipt = ProductImport(staff_id=staff_id)
        db.session.add(import_receipt)


        for product_data in products_data:
            detail = ProductImportDetail(
                import_receipt=import_receipt,
                product_id=product_data['product_id'],
                quantity=product_data['quantity']
            )
            db.session.add(detail)


            product = Product.query.get(product_data['product_id'])
            product.quantity_in_stock += product_data['quantity']

        import_receipt.calculate_total_quantity()
        db.session.commit()
        return True, "Import successful"

    except Exception as e:
        db.session.rollback()
        return False, f"Error during import: {str(e)}"


if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)
