import uuid
from django.db import models
from django.conf import settings
from apps.rooms.models import Room


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Abierto'
        CLOSED = 'closed', 'Cerrado'

    class PhotoStatus(models.TextChoices):
        PENDING  = 'pending',  'Pendiente'
        UPLOADED = 'uploaded', 'Subida'
        FAILED   = 'failed',   'Fallida'
        NA       = 'na',       'No aplica'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='attendance_records'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='attendance_records'
    )

    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    hours_worked = models.FloatField(null=True, blank=True)

    photo_url = models.URLField(max_length=500, blank=True, default='')
    photo_status = models.CharField(
        max_length=10,
        choices=PhotoStatus.choices,
        default=PhotoStatus.NA,
        help_text='Estado de la subida de la foto a Google Drive'
    )

    lat_checkin = models.FloatField()
    lon_checkin = models.FloatField()
    lat_checkout = models.FloatField(null=True, blank=True)
    lon_checkout = models.FloatField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        db_table = 'attendance_records'
        verbose_name = 'Registro de asistencia'
        verbose_name_plural = 'Registros de asistencia'
        ordering = ['-check_in']

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.check_in.date()} [{self.status}]'

    def calculate_hours(self):
        if self.check_out and self.check_in:
            delta = self.check_out - self.check_in
            return round(delta.total_seconds() / 3600, 2)
        return None


class SystemGoogleToken(models.Model):
    token_json = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Google Drive Token"

    @classmethod
    def get(cls):
        return cls.objects.first()

    @classmethod
    def save_from_creds(cls, creds):
        import json
        data = {
            'token':         creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri':     creds.token_uri,
            'client_id':     creds.client_id,
            'client_secret': creds.client_secret,
            'scopes':        list(creds.scopes),
            'expiry':        creds.expiry.isoformat() if creds.expiry else None,
        }
        cls.objects.update_or_create(id=1, defaults={'token_json': json.dumps(data)})