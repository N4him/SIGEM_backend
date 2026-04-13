from rest_framework import serializers
from .models import AttendanceRecord


class CheckInSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

class CheckOutSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    photo = serializers.ImageField(required=False)
    


class AttendanceRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'user_name', 'room_name',
            'check_in', 'check_out', 'hours_worked',
            'photo_url', 'status',
            'lat_checkin', 'lon_checkin',
        ]