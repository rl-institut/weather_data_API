from django.urls import path
from . import views

app_name = "data"
urlpatterns = [
    path("", views.coordinates_form, name="coordinates_form"),
    path("download/", views.download_file, name="download_file"),
]
