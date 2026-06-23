from django.contrib import admin
from .models import Table, Order, OrderLine, Payment

class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "seats", "status")
    list_filter = ("tenant", "status")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "source", "status", "table", "total", "created_at")
    list_filter = ("tenant", "source", "status")
    inlines = [OrderLineInline, PaymentInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "tenant", "method", "amount", "created_at")
    list_filter = ("tenant", "method")
