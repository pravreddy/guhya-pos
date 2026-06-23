from django.contrib import admin
from django.urls import path, include
from django.db import connection
from django.http import JsonResponse


def ping(request):
    return JsonResponse({"status": "ok"})


def ping_db(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"db": "ok"})
    except Exception:
        return JsonResponse({"db": "error"}, status=503)


urlpatterns = [
    path("ping", ping),
    path("ping/db", ping_db),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
