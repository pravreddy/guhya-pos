from django.db import models
from .current import get_current_tenant

class Tenant(models.Model):
    """One restaurant. Everything else is scoped to a Tenant."""
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    # --- per-restaurant payment config (owner sets these in Settings; nothing
    # is hardcoded). The UPI QR at billing switches on once upi_vpa is filled. ---
    upi_vpa = models.CharField(max_length=80, blank=True)        # e.g. cafegopala@okhdfcbank
    upi_payee_name = models.CharField(max_length=80, blank=True)  # shown in the customer's UPI app
    whatsapp_number = models.CharField(max_length=20, blank=True)  # restaurant's WhatsApp/contact, shown on the bill
    # tax / GST config — small eateries may not charge GST at all, and the rate
    # isn't always 5%. Owner sets these in Settings.
    gst_enabled = models.BooleanField(default=True)
    default_gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class TenantQuerySet(models.QuerySet):
    def for_current(self):
        """Use in API/views to return ONLY the current restaurant's rows.
        Returns nothing if there is no tenant context (safe default)."""
        tenant = get_current_tenant()
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)

class TenantAwareModel(models.Model):
    """Base class: gives every model a tenant and auto-fills it on save."""
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE)
    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.tenant_id is None:
            self.tenant = get_current_tenant()
        super().save(*args, **kwargs)
