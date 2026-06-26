from decimal import Decimal
from rest_framework import serializers
from tenancy.models import Tenant
from accounts.models import User, Attendance
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


class MenuCategoryAdminSerializer(serializers.ModelSerializer):
    """Full category for the owner's menu manager (incl. inactive)."""
    class Meta:
        model = MenuCategory
        fields = ["id", "name", "sort_order", "is_active"]


class MenuItemAdminSerializer(serializers.ModelSerializer):
    """Writable item for the menu manager. Category must belong to the tenant."""
    class Meta:
        model = MenuItem
        fields = ["id", "name", "category", "price", "half_price",
                  "food_type", "gst_rate", "is_available"]

    def validate_category(self, value):
        if not MenuCategory.objects.for_current().filter(pk=value.pk).exists():
            raise serializers.ValidationError("Category not found.")
        return value


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["id", "name", "seats", "status", "qr_token"]


class TableAdminSerializer(serializers.ModelSerializer):
    """Owner/admin writable table. status is system-managed; qr_token auto."""
    class Meta:
        model = Table
        fields = ["id", "name", "seats", "status"]
        read_only_fields = ["status"]


class UserAdminSerializer(serializers.ModelSerializer):
    """Owner/admin manage staff logins for their restaurant. Password is
    write-only; required on create, optional on update (reset)."""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "role", "is_active", "password",
                  "wage_type", "wage_rate", "attendance_pin"]

    def validate_role(self, value):
        if value == User.Role.OWNER:
            raise serializers.ValidationError("You can't create another owner here.")
        return value

    def create(self, validated_data):
        pwd = (validated_data.pop("password", "") or "").strip()
        if not pwd:
            raise serializers.ValidationError({"password": "Password is required for a new user."})
        user = User(**validated_data)   # tenant comes from serializer.save(tenant=...)
        user.set_password(pwd)
        user.save()
        return user

    def update(self, instance, validated_data):
        pwd = validated_data.pop("password", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if pwd:
            instance.set_password(pwd)
        instance.save()
        return instance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.username", read_only=True)
    hours = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "clock_in", "clock_out",
                  "hours", "source"]

    def get_hours(self, obj):
        return obj.hours


class TenantSettingsSerializer(serializers.ModelSerializer):
    """Per-restaurant settings the owner configures (UPI for now; branding etc.
    later). Readable by any tenant user so the cashier can build the UPI QR."""
    class Meta:
        model = Tenant
        fields = ["id", "name", "upi_vpa", "upi_payee_name", "whatsapp_number",
                  "gst_enabled", "default_gst_rate"]
        read_only_fields = ["id"]


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
    customer_phone = serializers.CharField(source="customer.phone", read_only=True, default=None)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    customer_email = serializers.CharField(source="customer.email", read_only=True, default=None)
    customer_telegram = serializers.CharField(source="customer.telegram", read_only=True, default=None)
    customer_consent = serializers.BooleanField(source="customer.marketing_consent", read_only=True, default=None)
    amount_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "table", "table_name", "source", "service_mode",
                  "token", "status",
                  "customer", "customer_phone", "customer_name",
                  "customer_email", "customer_telegram", "customer_consent",
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
