from django.urls import path
from . import views

app_name = "coordsapp"

urlpatterns = [
    path("", views.coordinates_form, name="coordinates_form"),
    path("pps/", views.pps_weather_data, name="pps_weather_data"),
    path("download/", views.download_file, name="download_file"),
    path("get_csrf_token/", views.get_csrf_token, name="get_csrf_token"),
    path("imprint/", views.imprint, name="imprint"),
    path("privacy/", views.privacy, name="privacy"),
]
