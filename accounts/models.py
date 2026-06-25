from django.contrib.auth.models import AbstractUser
from django.db import models
from tenancy.models import TenantAwareModel

class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        CASHIER = "cashier", "Cashier"
        KITCHEN = "kitchen", "Kitchen"
        WAITER = "waiter", "Waiter"

    class WageType(models.TextChoices):
        MONTHLY = "monthly", "Monthly salary"
        DAILY = "daily", "Daily wage"
        HOURLY = "hourly", "Hourly wage"

    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True,
        on_delete=models.CASCADE, related_name="users",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)
    # --- payroll ---
    wage_type = models.CharField(max_length=10, choices=WageType.choices,
                                 default=WageType.MONTHLY)
    # rupees per month / per day / per hour, read according to wage_type
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # short PIN for clocking in/out on a shared device. NOT a security boundary,
    # just to make casual buddy-punching a little harder.
    attendance_pin = models.CharField(max_length=6, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Attendance(TenantAwareModel):
    """One clock-in / clock-out pair. Times are stamped by the SERVER, so staff
    can't fake their arrival time. A biometric (fingerprint) device can later
    push punches into this same table via the same fields."""
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance")
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)
    # "manual" today; "fingerprint" later when a device feeds this.
    source = models.CharField(max_length=20, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-clock_in"]

    @property
    def hours(self):
        if self.clock_out:
            return round((self.clock_out - self.clock_in).total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.employee.username} @ {self.clock_in:%Y-%m-%d %H:%M}"
