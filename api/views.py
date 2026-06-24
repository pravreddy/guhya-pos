from decimal import Decimal, InvalidOperation
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import ProtectedError
from rest_framework import viewsets, permissions
from rest_framework.decorators import (
    action, api_view, permission_classes, authentication_classes,
)
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from tenancy.current import set_current_tenant
from accounts.models import User
from catalog.models import MenuCategory, MenuItem
from orders.models import Table, Order, OrderLine, Payment
from .serializers import (
    MenuCategorySerializer, TableSerializer, OrderSerializer,
    MenuCategoryAdminSerializer, MenuItemAdminSerializer,
)


class HasTenant(permissions.BasePermission):
    """Authenticated AND linked to a restaurant."""
    message = "Your account isn't linked to a restaurant."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, "tenant_id", None))


class IsOwnerOrAdmin(permissions.BasePermission):
    """Menu management is owner/admin only — a cashier shouldn't edit the menu."""
    message = "Only an owner or admin can manage the menu."

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and getattr(u, "tenant_id", None)
            and getattr(u, "role", None) in (User.Role.OWNER, User.Role.ADMIN)
        )


class TenantViewMixin:
    """Pin the current restaurant for this request, AFTER auth has run.
    (Token auth resolves the user inside the view, not in middleware.)"""
    permission_classes = [HasTenant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        set_current_tenant(getattr(request.user, "tenant", None))


@api_view(["POST"])
@authentication_classes([])  # no session auth on login -> no CSRF (SPA uses tokens)
@permission_classes([permissions.AllowAny])
def login(request):
    user = authenticate(
        username=request.data.get("username"),
        password=request.data.get("password"),
    )
    if not user:
        return Response({"detail": "Invalid username or password."}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    tenant = getattr(user, "tenant", None)
    return Response({
        "token": token.key,
        "username": user.username,
        "role": getattr(user, "role", None),
        "tenant": {"id": tenant.id, "name": tenant.name} if tenant else None,
    })


class MenuViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuCategorySerializer

    def get_queryset(self):
        return (MenuCategory.objects.for_current()
                .filter(is_active=True).prefetch_related("items"))


class MenuCategoryAdminViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """Owner/admin CRUD for menu categories (returns ALL, incl. inactive)."""
    serializer_class = MenuCategoryAdminSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return MenuCategory.objects.for_current()

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This category still has items. Delete or move them first."},
                status=400,
            )


class MenuItemAdminViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """Owner/admin CRUD for menu items (returns ALL, incl. unavailable)."""
    serializer_class = MenuItemAdminSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return MenuItem.objects.for_current().select_related("category")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This item is used in past orders. "
                           "Mark it unavailable instead of deleting."},
                status=400,
            )


class TableViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TableSerializer

    def get_queryset(self):
        return Table.objects.for_current()


class OrderViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    http_method_names = ["get", "post"]  # mutations happen through the actions below

    def get_queryset(self):
        qs = (Order.objects.for_current()
              .select_related("table").prefetch_related("lines", "payments"))
        s = self.request.query_params.get("status")
        if s == "active":
            qs = qs.exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])
        elif s:
            qs = qs.filter(status=s)
        return qs

    # --- helpers: always serialize a FRESH read (no stale prefetch cache) ---
    def _fresh(self, pk):
        return Order.objects.select_related("table").get(pk=pk)

    def _respond(self, pk, recalc=False):
        order = self._fresh(pk)
        if recalc:
            order.recalculate()
        return Response(OrderSerializer(order).data)

    def create(self, request, *args, **kwargs):
        table = None
        if request.data.get("table_id"):
            table = Table.objects.for_current().filter(pk=request.data["table_id"]).first()
            if not table:
                return Response({"detail": "Table not found."}, status=404)
        source = request.data.get("source", Order.Source.DINE_IN)
        if source not in Order.Source.values:
            return Response({"detail": "Invalid source."}, status=400)
        order = Order.objects.create(table=table, source=source)
        if table and source == Order.Source.DINE_IN:
            table.status = Table.Status.OCCUPIED
            table.save(update_fields=["status"])
        return Response(OrderSerializer(order).data, status=201)

    @action(detail=True, methods=["post"])
    def add_line(self, request, pk=None):
        order = self.get_object()
        if order.status in [Order.Status.PAID, Order.Status.CANCELLED]:
            return Response({"detail": "This order is closed."}, status=400)
        item = MenuItem.objects.for_current().filter(pk=request.data.get("item_id")).first()
        if not item:
            return Response({"detail": "Item not found."}, status=404)
        try:
            qty = max(1, int(request.data.get("qty", 1)))
        except (TypeError, ValueError):
            qty = 1
        is_half = bool(request.data.get("is_half", False))
        notes = (request.data.get("notes") or "").strip()
        with transaction.atomic():
            existing = order.lines.filter(
                item=item, is_half=is_half, notes=notes, status=OrderLine.Status.NEW,
            ).first()
            if existing:
                existing.qty += qty
                existing.save()
            else:
                OrderLine.objects.create(order=order, item=item, qty=qty,
                                         is_half=is_half, notes=notes)
        return self._respond(order.pk, recalc=True)

    @action(detail=True, methods=["post"])
    def update_line(self, request, pk=None):
        order = self.get_object()
        line = order.lines.filter(pk=request.data.get("line_id")).first()
        if not line:
            return Response({"detail": "Line not found."}, status=404)
        if "qty" in request.data:
            try:
                q = int(request.data["qty"])
            except (TypeError, ValueError):
                return Response({"detail": "Invalid qty."}, status=400)
            if q <= 0:
                line.delete()
                return self._respond(order.pk, recalc=True)
            line.qty = q
        if request.data.get("status") in OrderLine.Status.values:
            line.status = request.data["status"]
        if "notes" in request.data:
            line.notes = (request.data["notes"] or "").strip()
        line.save()
        return self._respond(order.pk, recalc=True)

    @action(detail=True, methods=["post"])
    def remove_line(self, request, pk=None):
        order = self.get_object()
        line = order.lines.filter(pk=request.data.get("line_id")).first()
        if line:
            line.delete()
        return self._respond(order.pk, recalc=True)

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        order = self.get_object()
        new = request.data.get("status")
        if new not in Order.Status.values:
            return Response({"detail": "Invalid status."}, status=400)
        order.status = new
        order.save(update_fields=["status", "updated_at"])
        if new == Order.Status.CANCELLED and order.table_id:
            order.table.status = Table.Status.FREE
            order.table.save(update_fields=["status"])
        return self._respond(order.pk)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        order = self.get_object()
        method = request.data.get("method", Payment.Method.CASH)
        if method not in Payment.Method.values:
            return Response({"detail": "Invalid payment method."}, status=400)
        try:
            amount = Decimal(str(request.data.get("amount", order.total)))
        except (InvalidOperation, TypeError):
            return Response({"detail": "Invalid amount."}, status=400)
        Payment.objects.create(order=order, method=method, amount=amount)
        fresh = self._fresh(order.pk)
        paid = sum((p.amount for p in fresh.payments.all()), Decimal("0"))
        if paid >= fresh.total:
            fresh.status = Order.Status.PAID
            fresh.save(update_fields=["status", "updated_at"])
            if fresh.table_id:
                fresh.table.status = Table.Status.FREE
                fresh.table.save(update_fields=["status"])
        return Response(OrderSerializer(fresh).data)

    @action(detail=False, methods=["get"])
    def kitchen(self, request):
        qs = self.get_queryset().filter(
            status__in=[Order.Status.NEW, Order.Status.PREPARING, Order.Status.READY]
        )
        return Response(OrderSerializer(qs, many=True).data)
