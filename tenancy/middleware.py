from .current import set_current_tenant

class CurrentTenantMiddleware:
    """Reads the tenant off the logged-in user and makes it available
    everywhere via request.tenant and tenancy.current.get_current_tenant()."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            tenant = getattr(user, "tenant", None)
        request.tenant = tenant
        set_current_tenant(tenant)
        try:
            return self.get_response(request)
        finally:
            set_current_tenant(None)
