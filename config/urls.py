from functools import lru_cache
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path, include
from django.db import connection
from django.http import JsonResponse, HttpResponse


def ping(request):
    return JsonResponse({"status": "ok"})


def ping_db(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"db": "ok"})
    except Exception:
        return JsonResponse({"db": "error"}, status=503)


@lru_cache(maxsize=1)
def _spa_html():
    # Served as a RAW file (not through the Django template engine), because the
    # app's JS uses ${{ ... }} object literals that the template engine would try
    # to parse as {{ variable }} tags. Cached; the container restarts on deploy.
    return (settings.BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


def spa(request):
    return HttpResponse(_spa_html())


urlpatterns = [
    path("ping", ping),
    path("ping/db", ping_db),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    # SPA catch-all: anything not starting with api/, admin/, or static/.
    re_path(r"^(?!api/|admin/|static/).*$", spa, name="spa"),
]
