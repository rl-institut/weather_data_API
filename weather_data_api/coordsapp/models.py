from django.db import models

# Create your models here.

class WeatherData(models.Model):
    dt = models.DateTimeField()
    lat = models.FloatField()
    lon = models.FloatField()
    wind_speed = models.FloatField(null=True, blank=True)
    temp_air = models.FloatField(null=True, blank=True)
    ghi = models.FloatField(null=True, blank=True)
    dni = models.FloatField(null=True, blank=True)
    dhi = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("dt", "lat", "lon")

    def __str__(self):
        return f"WeatherData({self.dt}, {self.lat}, {self.lon})"
