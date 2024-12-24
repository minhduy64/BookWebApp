from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Enum, DateTime
from sqlalchemy.orm import relationship
from app import db, app
from enum import Enum as RoleEnum
from flask_login import UserMixin
from datetime import datetime, timedelta


class UserRole(RoleEnum):
    ADMIN = 1
    STAFF = 2
    CUSTOMER = 3


class User(db.Model, UserMixin):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))
    email = Column(String(100), nullable=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(50), nullable=False)
    phone_number = Column(String(15), nullable=True)
    avatar = Column(String(100),
                    default='https://res.cloudinary.com/dehkjrhjw/image/upload/v1732357374/admin_ezrocx.jpg')
    user_role = Column(Enum(UserRole), default=UserRole.CUSTOMER)

    # Add relationships

    product_imports = relationship('ProductImport', backref='created_by', lazy=True)
    orders = relationship('Order', backref='customer', lazy=True)
    comments = relationship('Comment', backref='user', lazy=True)


class Category(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True)
    products = relationship('Product', backref='category', lazy=True)

    def __str__(self):
        return self.name


class Product(db.Model):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    author = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    price = Column(Float, default=0)
    image = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    quantity_in_stock = Column(Integer, default=0)

    # Relationships
    import_details = relationship('ProductImportDetail', backref='product', lazy=True)
    order_details = relationship('OrderDetail', backref='product', lazy=True)
    comments = relationship('Comment', backref='product', lazy=True)

    def __str__(self):
        return self.name


class ProductImport(db.Model):
    __tablename__ = 'product_import'

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_date = Column(DateTime, default=datetime.now(), nullable=False)
    staff_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    total_quantity = Column(Integer, default=0)
    notes = Column(String(255))

    # Relationships
    details = relationship('ProductImportDetail', backref='import_receipt', lazy=True,
                           cascade="all, delete-orphan")

    def calculate_total_quantity(self):
        self.total_quantity = sum(detail.quantity for detail in self.details)


class ProductImportDetail(db.Model):
    __tablename__ = 'product_import_detail'

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_id = Column(Integer, ForeignKey('product_import.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False)

    def update_product_stock(self):
        if self.product:
            self.product.quantity_in_stock += self.quantity


class OrderStatus(RoleEnum):
    PENDING = 1
    CONFIRMED = 2
    PAID = 3
    SHIPPING = 4
    COMPLETED = 5
    CANCELLED = 6


class PaymentMethod(RoleEnum):
    ONLINE = 1
    STORE_PICKUP = 2


class Order(db.Model):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    order_date = Column(DateTime, default=datetime.now)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    delivery_address = Column(String(255), nullable=True)
    pickup_deadline = Column(DateTime, nullable=True)
    total_amount = Column(Float, default=0)

    # Relationship
    details = relationship('OrderDetail', backref='order', lazy=True,
                           cascade="all, delete-orphan")

    def calculate_pickup_deadline(self):
        #Tính thời hạn nhận hàng dựa trên ngày đặt hàng
        if self.payment_method == PaymentMethod.STORE_PICKUP:
            self.pickup_deadline = self.order_date + timedelta(hours=48)

    def calculate_total(self):
        #Tính tổng số tiền đặt hàng
        self.total_amount = sum(detail.price * detail.quantity for detail in self.details)


class OrderDetail(db.Model):
    __tablename__ = 'order_detail'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    def update_product_stock(self):
        if self.product:
            self.product.quantity_in_stock -= self.quantity


class Comment(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(255), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.now)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            import hashlib

            admin = User(
                name='admin',
                email='admin@gmail.com',
                username='admin',
                phone_number='0123456789',
                password=str(hashlib.md5('123456'.encode('utf-8')).hexdigest()),
                user_role=UserRole.ADMIN
            )
            db.session.add(admin)

        categories = ['Văn học', 'Kỹ năng sống', 'Kinh tế', 'Thiếu nhi']
        for cate_name in categories:
            if not Category.query.filter_by(name=cate_name).first():
                category = Category(name=cate_name)
                db.session.add(category)

        products = [
            {
                "name": "Nhà Giả Kim",
                "author": "Paulo Coelho",
                "image": "https://res.cloudinary.com/dehkjrhjw/image/upload/v1732361940/nhagiakim_cnfihh.jpg",
                "category_id": 1,
                "quantity_in_stock": 50,
                "price": 88000
            },
            {
                "name": "Đắc Nhân Tâm",
                "author": "Dale Carnegie",
                "category_id": 2,
                "description": "Đắc nhân tâm của Dale Carnegie là quyển sách nổi tiếng nhất, bán chạy nhất và có tầm ảnh hưởng nhất của mọi thời đại. Tác phẩm đã được chuyển ngữ sang hầu hết các thứ tiếng trên thế giới và có mặt ở hàng trăm quốc gia."
                [:255],
                "image": "https://res.cloudinary.com/dehkjrhjw/image/upload/v1734923439/Dac-nhan-tam.jpg",
                "quantity_in_stock": 100,
                "price": 76000
            },
            {
                "name": "Think and Grow Rich",
                "author": "Napoleon Hill",
                "category_id": 3,
                "image": "https://res.cloudinary.com/dehkjrhjw/image/upload/v1734922939/thinkandgrowrich.webp",
                "quantity_in_stock": 75,
                "price": 120000
            },
            {
                "name": "Doraemon Tập 1",
                "author": "Fujiko F. Fujio",
                "category_id": 4,
                "image": "https://res.cloudinary.com/dehkjrhjw/image/upload/v1734922983/dorameont1.webp",
                "quantity_in_stock": 150,
                "price": 25000
            },
            {
                "name": "Doraemon Tập 2",
                "author": "Fujiko F. Fujio",
                "category_id": 4,
                "image": "https://res.cloudinary.com/dehkjrhjw/image/upload/v1734923531/doraemontap2_mle3zm.jpg",
                "quantity_in_stock": 150,
                "price": 25000
            }
        ]

        for product_data in products:
            product = Product(**product_data)
            db.session.add(product)

        db.session.commit()