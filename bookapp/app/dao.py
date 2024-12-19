from app.models import Category, Product, User, Order, OrderDetail
from app import app, db
import hashlib
import cloudinary.uploader
from flask_login import current_user


def load_categories():
    return Category.query.order_by('id').all()


def load_products(cate_id=None, kw=None, page=1):
    query = Product.query

    if kw:
        query = query.filter(Product.title.contains(kw))

    if cate_id:
        query = query.filter(Product.category_id == cate_id)

    page_size = app.config['PAGE_SIZE']
    start = (page - 1) * page_size
    query = query.slice(start, start + page_size)

    return query.all()


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
        r = Order(user=current_user)
        db.session.add(r)

        for c in cart.values():
            d = OrderDetail(quantity=c['quantity'], unit_price=c['price'],
                            product_id=c['id'], receipt=r)
            db.session.add(d)

        db.session.commit()
