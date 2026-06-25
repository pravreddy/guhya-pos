from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("menu", views.MenuViewSet, basename="menu")
router.register("menu-categories", views.MenuCategoryAdminViewSet, basename="menu-categories")
router.register("menu-items", views.MenuItemAdminViewSet, basename="menu-items")
router.register("tables", views.TableViewSet, basename="tables")
router.register("tables-admin", views.TableAdminViewSet, basename="tables-admin")
router.register("users-admin", views.UserAdminViewSet, basename="users-admin")
router.register("orders", views.OrderViewSet, basename="orders")

urlpatterns = [
    path("auth/login/", views.login, name="api-login"),
    path("menu-import/", views.MenuImportView.as_view(), name="menu-import"),
    path("menu-export/", views.MenuExportView.as_view(), name="menu-export"),
    path("attendance/employees/", views.AttendanceEmployeesView.as_view(), name="attendance-employees"),
    path("attendance/punch/", views.AttendancePunchView.as_view(), name="attendance-punch"),
    path("attendance/summary/", views.AttendanceSummaryView.as_view(), name="attendance-summary"),
    path("attendance/", views.AttendanceListView.as_view(), name="attendance-list"),
    path("tenant/", views.TenantSettingsView.as_view(), name="tenant-settings"),
] + router.urls
