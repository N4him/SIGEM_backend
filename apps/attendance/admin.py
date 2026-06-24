from django.contrib import admin
from .models import AttendanceRecord
from .models import SystemGoogleToken

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'check_in', 'check_out', 'hours_worked', 'status']
    list_filter = ['status', 'room', 'photo_status']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['hours_worked', 'photo_url', 'photo_status']



@admin.register(SystemGoogleToken)
class SystemGoogleTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated_at']
    readonly_fields = ['token_json', 'updated_at']