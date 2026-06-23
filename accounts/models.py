from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        CASHIER = "cashier", "Cashier"
        KITCHEN = "kitchen", "Kitchen"
        WAITER = "waiter", "Waiter"

    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True,
        on_delete=models.CASCADE, related_name="users",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)

    def __str__(self):
        return f"{self.username} ({self.role})"
