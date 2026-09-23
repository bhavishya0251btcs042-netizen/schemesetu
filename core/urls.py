from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("check/", views.check, name="check"),
    path("results/", views.results, name="results"),
    path("scheme/<int:pk>/", views.scheme_detail, name="scheme_detail"),
    path("scheme/<int:pk>/apply/", views.apply, name="apply"),
    path("application/<str:tracking_id>/", views.application_detail, name="application_detail"),
    path("track/", views.track, name="track"),
    path("notifications/", views.notifications_inbox, name="notifications"),
]
