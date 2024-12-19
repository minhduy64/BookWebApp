from app import db, app, dao
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from app.models import Category, Product, User, UserRole
from flask_login import current_user, logout_user
from flask_admin import BaseView, expose
from flask import redirect


class MyAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render('admin/index.html')#, cates=dao.stats_products())


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
    pass


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
        # stats = dao.revenue_stats()
        # stats2 = dao.period_stats()
         return self.render('admin/stats.html')#,stats=stats, stats2=stats2)


admin.add_view(CategoryView(Category, db.session))
admin.add_view(ProductView(Product, db.session))
admin.add_view(AuthenticatedView(User, db.session))
admin.add_view(StatsView(name='Thống kê - báo cáo'))
admin.add_view(LogoutView(name='Đăng xuất'))