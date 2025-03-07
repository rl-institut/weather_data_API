from django.urls import path
from . import views

app_name = "coordsapp"

urlpatterns = [
    path("", views.coordinates_form, name="coordinates_form"),
    path("pps/", views.pps_weather_data, name="pps_weather_data"),
    path("download/", views.download_file, name="download_file"),
]
