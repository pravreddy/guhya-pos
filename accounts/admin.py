from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "tenant", "role", "is_staff")
    list_filter = ("tenant", "role", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("Restaurant", {"fields": ("tenant", "role")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Restaurant", {"fields": ("tenant", "role")}),)
