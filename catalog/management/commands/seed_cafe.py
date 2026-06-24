"""
Seed a demo restaurant so the app is usable immediately (no admin needed).

    docker exec guhya-pos-api-blue python manage.py seed_cafe

Idempotent: safe to run more than once. Creates:
  - tenant "Cafe Gopala"
  - links any superuser (no tenant) to it as owner, so you can log in
  - demo logins  cashier/cashier123  and  kitchen/kitchen123
  - tables T1-T6
  - a starter South-Indian menu (GST 5%)
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from tenancy.models import Tenant
from accounts.models import User
from catalog.models import MenuCategory, MenuItem
from orders.models import Table

# name, price, half_price (or None), food_type, gst_rate
MENU = {
    "Tiffins": [
        ("Idli (2 pc)", "30", None, "veg", "5"),
        ("Plain Dosa", "60", None, "veg", "5"),
        ("Masala Dosa", "80", None, "veg", "5"),
        ("Rava Dosa", "90", None, "veg", "5"),
        ("Medu Vada (2 pc)", "40", None, "veg", "5"),
        ("Pongal", "70", None, "veg", "5"),
    ],
    "Rice & Meals": [
        ("Curd Rice", "70", None, "veg", "5"),
        ("Lemon Rice", "70", None, "veg", "5"),
        ("Veg Biryani", "140", "90", "veg", "5"),
        ("Egg Biryani", "160", "100", "egg", "5"),
        ("Full Meals", "150", None, "veg", "5"),
    ],
    "Beverages": [
        ("Filter Coffee", "30", None, "veg", "5"),
        ("Tea", "20", None, "veg", "5"),
        ("Buttermilk", "25", None, "veg", "5"),
    ],
}


class Command(BaseCommand):
    help = "Seed a demo restaurant (Cafe Gopala): tenant, users, tables, menu."

    @transaction.atomic
    def handle(self, *args, **opts):
        tenant, created = Tenant.objects.get_or_create(
            slug="cafe-gopala", defaults={"name": "Cafe Gopala"})
        self.stdout.write(("Created" if created else "Found") + f" tenant: {tenant.name}")

        # Link any tenant-less superuser so the admin account can use the app (as owner).
        for su in User.objects.filter(is_superuser=True, tenant__isnull=True):
            su.tenant = tenant
            su.role = User.Role.OWNER
            su.save(update_fields=["tenant", "role"])
            self.stdout.write(f"Linked superuser '{su.username}' -> {tenant.name} (owner)")

        # Demo staff logins for testing role-based screens.
        for uname, role in [("cashier", User.Role.CASHIER), ("kitchen", User.Role.KITCHEN)]:
            u, c = User.objects.get_or_create(
                username=uname, defaults={"tenant": tenant, "role": role})
            if c:
                u.set_password(uname + "123")
                u.tenant = tenant
                u.role = role
                u.save()
                self.stdout.write(f"Created login  {uname}/{uname}123  ({role})")

        # Tables T1-T6
        for i in range(1, 7):
            Table.objects.get_or_create(tenant=tenant, name=f"T{i}", defaults={"seats": 4})
        self.stdout.write("Tables T1-T6 ready")

        # Menu
        for si, (cat_name, items) in enumerate(MENU.items()):
            cat, _ = MenuCategory.objects.get_or_create(
                tenant=tenant, name=cat_name, defaults={"sort_order": si})
            for name, price, half, ftype, gst in items:
                MenuItem.objects.get_or_create(
                    tenant=tenant, category=cat, name=name,
                    defaults={"price": price, "half_price": half,
                              "food_type": ftype, "gst_rate": gst})

        self.stdout.write(self.style.SUCCESS(
            f"Done. Log in at the app as your superuser (owner), "
            f"or cashier/cashier123, or kitchen/kitchen123."))
