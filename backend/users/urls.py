from django.urls import path
from . import views
from . import views_admin

urlpatterns = [
    path("whoami/", views.whoami, name="whoami"),
    path("admin/", views.admin_site, name="admin_site"),
    path("role-redirect/", views.role_redirect, name="role-redirect"),
    path("admin/manage/", views_admin.AdminUserList.as_view(), name="admin_user_list"),
    path("admin/manage<int:pk>/", views_admin.AdminUserRoleUpdate.as_view(), name="admin_user_role_update"),
    path("csrf/", views.csrf_token, name="csrf_token")
]