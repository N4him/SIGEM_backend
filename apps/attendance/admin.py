from django.contrib import admin
from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'check_in', 'check_out', 'hours_worked', 'status']
    list_filter = ['status', 'room']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['hours_worked', 'photo_url']