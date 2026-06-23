"""Holds the 'current restaurant' for the duration of one request."""
import threading

_state = threading.local()

def set_current_tenant(tenant):
    _state.tenant = tenant

def get_current_tenant():
    return getattr(_state, "tenant", None)
