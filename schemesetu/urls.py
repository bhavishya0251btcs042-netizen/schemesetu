from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),   # auth: /auth/signup/, /auth/login/, etc.
    path("", include("core.urls")),       # main app
]
