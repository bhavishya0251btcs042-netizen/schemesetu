import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),   # auth: /auth/signup/, /auth/login/, etc.
    path("", include("core.urls")),       # main app
    # Fallback to guarantee static files are served with correct MIME type
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
]
