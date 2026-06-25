from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("menu", views.MenuViewSet, basename="menu")
router.register("menu-categories", views.MenuCategoryAdminViewSet, basename="menu-categories")
router.register("menu-items", views.MenuItemAdminViewSet, basename="menu-items")
router.register("tables", views.TableViewSet, basename="tables")
router.register("orders", views.OrderViewSet, basename="orders")

urlpatterns = [
    path("auth/login/", views.login, name="api-login"),
    path("menu-import/", views.MenuImportView.as_view(), name="menu-import"),
] + router.urls
