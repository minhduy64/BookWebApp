from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from flask import redirect, url_for, flash
from werkzeug.routing import ValidationError

from app.models import UserRole, Category, Product, User, Order, OrderDetail
from app import db, app, dao


#Logout View
class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        flash('Bạn đã đăng xuất thành công.', 'success')
        return redirect('/admin')

    def is_accessible(self):
        return current_user.is_authenticated


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]

    def inaccessible_callback(self, name, **kwargs):
        flash('Vui lòng đăng nhập với đặc quyền.', 'error')
        return self.render('admin/index.html', categories=dao.stats_products())


class AdminOnlyView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN


class StaffProductView(AuthenticatedView):
    column_list = ['id', 'name', 'category', 'price', 'quantity_in_stock']
    can_create = False
    can_delete = False
    column_searchable_list = ['name']
    column_filters = ['price', 'quantity_in_stock']
    form_excluded_columns = ['orders', 'comments', 'image']


class AdminProductView(AdminOnlyView):
    column_list = ['id', 'name', 'category', 'price', 'category_id', 'author', 'quantity_in_stock']
    can_export = True
    column_searchable_list = ['name', 'author']
    column_filters = ['price', 'category_id', 'quantity_in_stock']
    column_editable_list = ['name', 'price', 'quantity_in_stock']


class OrderManagementView(AuthenticatedView):
    column_list = ['id', 'user_id', 'status', 'order_date', 'payment_method']
    column_filters = ['status', 'order_date', 'payment_method']
    can_create = False
    can_delete = False

    def on_model_change(self, form, model, is_created):
        if current_user.user_role == UserRole.STAFF:
            if form.status.data not in ['PENDING', 'CONFIRMED', 'SHIPPING']:
                raise ValidationError('Staff can only update to PENDING, CONFIRMED, or SHIPPING status')


class StatsView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]

    @expose('/')
    def index(self):
        stats = dao.revenue_stats()
        month_stats = dao.revenue_month_stats()
        month_category_stats = dao.revenue_month_stats_by_category()
        return self.render('admin/stats.html',
                         stats=stats,
                         month_stats=month_stats,
                         month_category_stats=month_category_stats)


class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]

    def inaccessible_callback(self, name, **kwargs):
        # Buộc đăng xuất khỏi mọi phiên hiện có
        if current_user.is_authenticated:
            logout_user()
        flash('Vui lòng đăng nhập bằng quản trị viên để truy cập.', 'warning')
        return self.render('admin/index.html')

    @expose("/")
    def index(self):
        return self.render('admin/index.html', categories=dao.stats_products())


class ImportView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]

    def inaccessible_callback(self, name, **kwargs):
        flash('Vui lòng đăng nhập bằng quản trị viên để truy cập.', 'error')
        return redirect(url_for('login'))

    @expose('/')
    def index(self):
        products = Product.query.all()
        return self.render('staff/import_products.html', products=products)


admin = Admin(app, name='AdminApp', template_mode='bootstrap4', index_view=SecureAdminIndexView())

# Register views
admin.add_view(AdminOnlyView(Category, db.session, name='Categories'))
admin.add_view(AdminProductView(Product, db.session, name='Products (Admin)'))
admin.add_view(StaffProductView(Product, db.session, name='Products (Staff)', endpoint='staff_products'))
admin.add_view(AdminOnlyView(User, db.session, name='Users'))
admin.add_view(OrderManagementView(Order, db.session, name='Orders'))
admin.add_view(AdminOnlyView(OrderDetail, db.session, name='Order Details'))
admin.add_view(ImportView(name='Import Products'))
admin.add_view(StatsView(name='Statistics'))
admin.add_view(LogoutView(name='Logout', endpoint='admin_logout'))