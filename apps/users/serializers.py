from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'phone', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        return CustomUser.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'role', 'phone', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at', 'role']


class UserAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_hours = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'role', 'phone', 'is_active', 'created_at', 'total_hours']
        read_only_fields = ['id', 'email', 'created_at', 'role']

    def get_total_hours(self, obj):
        from apps.attendance.models import AttendanceRecord
        records = AttendanceRecord.objects.filter(
            user=obj,
            status=AttendanceRecord.Status.CLOSED
        )
        total = sum(r.hours_worked or 0 for r in records)
        return round(total, 2)
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

class UserAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'is_active']