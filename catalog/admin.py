from django.contrib import admin
from .models import MenuCategory, MenuItem

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "sort_order", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("name",)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "category", "price", "half_price",
                    "food_type", "gst_rate", "is_available")
    list_filter = ("tenant", "category", "food_type", "is_available")
    search_fields = ("name",)
