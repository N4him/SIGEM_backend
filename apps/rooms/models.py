from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    allowed_radius_m = models.FloatField(default=50.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'rooms'
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'

    def __str__(self):
        return self.name