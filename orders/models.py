import uuid
from decimal import Decimal
from django.db import models
from tenancy.models import TenantAwareModel
from catalog.models import MenuItem

class Table(TenantAwareModel):
    class Status(models.TextChoices):
        FREE = "free", "Free"
        OCCUPIED = "occupied", "Occupied"
        RESERVED = "reserved", "Reserved"

    name = models.CharField(max_length=40)
    seats = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FREE)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.name

class Customer(TenantAwareModel):
    """A diner captured at billing (phone-first). Optional and skippable, but
    once captured it seeds the CRM: visit count, spend, last visit. Unique by
    phone within a restaurant."""
    phone = models.CharField(max_length=20)
    name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    telegram = models.CharField(max_length=64, blank=True)  # @username / chat handle
    # consent to be contacted for marketing (loyalty/offers). Kept from day one
    # so we never message people who didn't opt in.
    marketing_consent = models.BooleanField(default=False)
    # denormalised stats, updated when an order is fully paid:
    visit_count = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_order_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_order_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "phone"],
                                    name="uniq_customer_tenant_phone"),
        ]

    def __str__(self):
        return self.name or self.phone

class Order(TenantAwareModel):
    class Source(models.TextChoices):
        DINE_IN = "dine_in", "Dine-in"
        ONLINE = "online", "Online"
        AGGREGATOR = "aggregator", "Aggregator"

    class ServiceMode(models.TextChoices):
        # How the order is fulfilled in-house. A takeaway order has no table and
        # several can run at once; one code path serves both (table-less order).
        DINE_IN = "dine_in", "Dine-in"
        TAKEAWAY = "takeaway", "Takeaway"

    class Status(models.TextChoices):
        NEW = "new", "New"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        DELIVERED = "delivered", "Delivered"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    class DiscountType(models.TextChoices):
        NONE = "none", "None"
        FLAT = "flat", "Flat ₹"
        PERCENT = "percent", "Percent"

    table = models.ForeignKey(Table, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="orders")
    # optional diner attached at billing (CRM). SET_NULL so deleting a customer
    # never destroys the order history.
    customer = models.ForeignKey(Customer, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="orders")
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.DINE_IN)
    service_mode = models.CharField(max_length=10, choices=ServiceMode.choices,
                                    default=ServiceMode.DINE_IN)
    # pickup token for takeaway (optional; cashier generates it at payment).
    # Numbered per restaurant, per day, starting at 1.
    token = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    # for aggregator orders (Zomato/Swiggy), filled when synced or entered:
    aggregator_name = models.CharField(max_length=40, blank=True)
    external_ref = models.CharField(max_length=80, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # order-level discount, applied by owner/admin on the fly (flat ₹ or %).
    # discount_value = what was entered; discount_amount = the ₹ actually taken
    # off (computed in recalculate); discount_by = who authorised it (audit).
    discount_type = models.CharField(max_length=8, choices=DiscountType.choices,
                                     default=DiscountType.NONE)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True)
    discount_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.get_source_display()})"

    def recalculate(self, save=True):
        """Recompute totals from the lines. GST is added on top (exclusive).
        If the restaurant has GST disabled, tax is zero and total == subtotal.
        An order-level discount (owner/admin) comes off the subtotal first, then
        GST is charged on the discounted amount (discount-then-GST)."""
        subtotal = Decimal("0")
        tax = Decimal("0")
        gst_on = getattr(self.tenant, "gst_enabled", True) if self.tenant_id else True
        for line in self.lines.all():
            subtotal += line.line_total
            if gst_on:
                tax += line.line_total * (line.gst_rate or Decimal("0")) / Decimal("100")
        disc = Decimal("0")
        if self.discount_type == self.DiscountType.FLAT:
            disc = min(self.discount_value or Decimal("0"), subtotal)
        elif self.discount_type == self.DiscountType.PERCENT:
            disc = subtotal * (self.discount_value or Decimal("0")) / Decimal("100")
            if disc > subtotal:
                disc = subtotal
        if subtotal > 0 and disc > 0:
            tax = tax * (subtotal - disc) / subtotal      # GST on the discounted amount
        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.discount_amount = disc.quantize(Decimal("0.01"))
        self.tax_total = tax.quantize(Decimal("0.01"))
        self.total = (self.subtotal - self.discount_amount + self.tax_total).quantize(Decimal("0.01"))
        if save:
            self.save(update_fields=["subtotal", "discount_amount", "tax_total",
                                     "total", "updated_at"])

class OrderLine(TenantAwareModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    # snapshots so old bills don't change when the menu is edited later:
    name_snapshot = models.CharField(max_length=120, blank=True)
    is_half = models.BooleanField(default=False)
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    notes = models.CharField(max_length=200, blank=True)

    def save(self, *args, **kwargs):
        if self.item_id:
            if not self.name_snapshot:
                self.name_snapshot = self.item.name
            if self.unit_price is None:
                self.unit_price = (
                    self.item.half_price
                    if (self.is_half and self.item.half_price is not None)
                    else self.item.price
                )
            if self.gst_rate is None:
                self.gst_rate = self.item.gst_rate
        self.line_total = (self.unit_price or Decimal("0")) * self.qty
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.qty} x {self.name_snapshot}"

class Payment(TenantAwareModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_method_display()} {self.amount}"
