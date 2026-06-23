from decimal import Decimal
from rest_framework import serializers
from catalog.models import MenuCategory, MenuItem
from orders.models import Table, Order, OrderLine, Payment


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ["id", "name", "category", "price", "half_price",
                  "food_type", "gst_rate", "is_available"]


class MenuCategorySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = MenuCategory
        fields = ["id", "name", "sort_order", "items"]

    def get_items(self, obj):
        items = obj.items.filter(is_available=True)
        return MenuItemSerializer(items, many=True).data


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["id", "name", "seats", "status", "qr_token"]


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ["id", "item", "name_snapshot", "is_half", "qty",
                  "unit_price", "gst_rate", "line_total", "status", "notes"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    table_name = serializers.CharField(source="table.name", read_only=True, default=None)
    amount_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "table", "table_name", "source", "status",
                  "aggregator_name", "external_ref",
                  "subtotal", "tax_total", "total",
                  "amount_paid", "balance",
                  "created_at", "updated_at", "lines", "payments"]

    def _paid(self, obj):
        return sum((p.amount for p in obj.payments.all()), Decimal("0"))

    def get_amount_paid(self, obj):
        return self._paid(obj)

    def get_balance(self, obj):
        return obj.total - self._paid(obj)
