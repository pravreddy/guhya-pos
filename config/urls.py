from django.contrib import admin
from django.urls import path, re_path, include
from django.db import connection
from django.http import JsonResponse
from django.views.generic import TemplateView


def ping(request):
    return JsonResponse({"status": "ok"})


def ping_db(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"db": "ok"})
    except Exception:
        return JsonResponse({"db": "error"}, status=503)


# The single-page app shell. Served for "/" and any client-side route that
# isn't an API / admin / static path (handled by the catch-all below).
spa = TemplateView.as_view(template_name="index.html")

urlpatterns = [
    path("ping", ping),
    path("ping/db", ping_db),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # SPA catch-all: anything not starting with api/, admin/, or static/.
    re_path(r"^(?!api/|admin/|static/).*$", spa, name="spa"),
]
