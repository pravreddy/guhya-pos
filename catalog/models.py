from django.db import models
from tenancy.models import TenantAwareModel

class MenuCategory(TenantAwareModel):
    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

class MenuItem(TenantAwareModel):
    class FoodType(models.TextChoices):
        VEG = "veg", "Veg"
        NONVEG = "nonveg", "Non-veg"
        EGG = "egg", "Egg"

    category = models.ForeignKey(MenuCategory, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    half_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    food_type = models.CharField(max_length=10, choices=FoodType.choices, default=FoodType.VEG)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__sort_order", "name"]

    def __str__(self):
        return self.name
