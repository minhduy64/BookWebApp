from pstats import Stats

from app import db, app, dao
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from app.models import Category, Product, User, UserRole, Order, OrderDetail
from flask_login import current_user, logout_user
from flask_admin import BaseView, expose
from flask import redirect, url_for, flash


class MyAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render('admin/index.html', categories=dao.stats_products())


admin = Admin(app, name='AdminApp', template_mode='bootstrap4', index_view=MyAdminIndexView())


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role.__eq__(UserRole.ADMIN)


class CategoryView(AuthenticatedView):
    can_export = True
    column_searchable_list = ['id', 'name']
    column_filters = ['id', 'name']
    can_view_details = True
    column_list = ['name', 'products']


class ProductView(AuthenticatedView):
    column_list = ['id', 'name', 'price', 'category', 'author', 'quantity_in_stock']
    can_export = True
    column_searchable_list = ['name']
    column_filters = ['price', 'name']
    column_editable_list = ['name', 'price']
    details_modal = True
    edit_modal = True
    can_view_details = True


class OrderView(AuthenticatedView):
    column_list = ['id', 'user_id', 'status', 'payment_method']
    column_searchable_list = ['id', 'user_id', ]
    column_filters = ['order_date']


class OrderDetailView(AuthenticatedView):
    column_list = ['id', 'order_id', 'product_id', 'quantity', 'price']
    column_searchable_list = ['id', 'product_id']
    column_filters = ['order_id', 'product_id']


class MyView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated


class LogoutView(MyView):
    @expose("/")
    def index(self):
        logout_user()
        return redirect('/admin')


class StatsView(MyView):
    @expose("/")
    def index(self):
        stats = dao.revenue_stats()
        month_stats = dao.revenue_month_stats()
        month_category_stats = dao.revenue_month_stats_by_category()
        return self.render('admin/stats.html', stats=stats, month_stats=month_stats,
                           month_category_stats=month_category_stats)


class ImportView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]

    def inaccessible_callback(self, name, **kwargs):
        flash('Please log in with appropriate privileges to access this page.', 'error')
        return redirect(url_for('login'))

    @expose('/')
    def index(self):
        products = Product.query.all()
        return self.render('staff/import_products.html', products=products)


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role in [UserRole.ADMIN, UserRole.STAFF]


class AdminOnlyView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN


# Update the view registrations
admin.add_view(AdminOnlyView(Category, db.session))
admin.add_view(ProductView(Product, db.session))
admin.add_view(AdminOnlyView(User, db.session))
admin.add_view(AdminOnlyView(Order, db.session))
admin.add_view(AdminOnlyView(OrderDetail, db.session))
admin.add_view(ImportView(name='Import Products'))
admin.add_view(StatsView(name='Statistics'))
admin.add_view(LogoutView(name="Logout"))
