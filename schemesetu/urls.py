from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from core import views as core_views

urlpatterns = [
    # Top-priority static handlers to prevent any serverless 404 or MIME type issues
    path("static/css/style.css", core_views.serve_css),
    path("favicon.ico", core_views.favicon),

    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),   # auth: /auth/signup/, /auth/login/, etc.
    path("", include("core.urls")),       # main app

    # General static fallback
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
]
