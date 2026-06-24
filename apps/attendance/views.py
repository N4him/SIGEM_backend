from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from core.permissions import IsMonitor
from apps.rooms.models import Room
from .models import AttendanceRecord
from .serializers import CheckInSerializer, CheckOutSerializer, AttendanceRecordSerializer
from .services import validate_location, upload_photo_to_drive
from datetime import timedelta
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True), name='post')
class CheckInView(APIView):
    permission_classes = [IsMonitor]

    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1. Obtener sala
        try:
            room = Room.objects.get(pk=data['room_id'], is_active=True)
        except Room.DoesNotExist:
            return Response(
                {'error': 'Sala no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Verificar que no haya check-in abierto hoy
        today = timezone.now().date()
        with transaction.atomic():
            open_record = AttendanceRecord.objects.filter(
                user=request.user,
                status=AttendanceRecord.Status.OPEN,
                check_in__date=today
            ).exists()
            if open_record:
                return Response(
                    {'error': 'Ya tienes una jornada abierta hoy.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 3. Validar ubicación GPS
        if not validate_location(data['latitude'], data['longitude'], room):
            return Response(
                {'error': f'Estás fuera del radio permitido de {room.allowed_radius_m}m.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Crear registro sin foto
        record = AttendanceRecord.objects.create(
            user=request.user,
            room=room,
            check_in=timezone.now(),
            lat_checkin=data['latitude'],
            lon_checkin=data['longitude'],
            status=AttendanceRecord.Status.OPEN,
        )

        return Response(
            {'success': True, 'record': AttendanceRecordSerializer(record).data},
            status=status.HTTP_201_CREATED
        )


class CheckOutView(APIView):
    permission_classes = [IsMonitor]

    def post(self, request):
        serializer = CheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            record = AttendanceRecord.objects.get(
                user=request.user,
                status=AttendanceRecord.Status.OPEN
            )
        except AttendanceRecord.DoesNotExist:
            return Response(
                {'error': 'No tienes una jornada abierta.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Subir foto a Drive (fallo no bloquea el check-out)
        photo_url = ''
        photo_status = AttendanceRecord.PhotoStatus.NA
        if 'photo' in request.FILES:
            print(f"[Checkout] Foto recibida, subiendo a Drive...")

            photo_url = upload_photo_to_drive(request.FILES['photo'], request.user, record.room)
            if photo_url:
                photo_status = AttendanceRecord.PhotoStatus.UPLOADED
            else:
                photo_status = AttendanceRecord.PhotoStatus.FAILED
        else:
            print(f"[Checkout] No llegó foto")
        # Cerrar jornada
        record.check_out = timezone.now()
        record.lat_checkout = data['latitude']
        record.lon_checkout = data['longitude']
        record.hours_worked = record.calculate_hours()
        record.photo_url = photo_url or ''
        record.photo_status = photo_status
        record.status = AttendanceRecord.Status.CLOSED
        record.save()

        return Response(
            {'success': True, 'record': AttendanceRecordSerializer(record).data}
        )


class MyRecordsView(ListAPIView):
    permission_classes = [IsMonitor]
    serializer_class = AttendanceRecordSerializer

    def get_queryset(self):
        qs = AttendanceRecord.objects.filter(user=self.request.user)
        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        if from_date:
            qs = qs.filter(check_in__date__gte=from_date)
        if to_date:
            qs = qs.filter(check_in__date__lte=to_date)
        return qs

class WeeklySummaryView(APIView):
    permission_classes = [IsMonitor]

    def get(self, request):
        today = timezone.now().date()
        # Lunes de la semana actual
        monday = today - timedelta(days=today.weekday())

        days = []
        for i in range(6):  # Lunes a Viernes
            day = monday + timedelta(days=i)
            records = AttendanceRecord.objects.filter(
                user=request.user,
                status=AttendanceRecord.Status.CLOSED,
                check_in__date=day,
            )
            total_hours = sum(r.hours_worked or 0 for r in records)
            days.append({
                'day': ['L', 'M', 'X', 'J', 'V', 'S'][i],
                'date': day.isoformat(),
                'hours': round(total_hours, 2),
                'is_today': day == today,
            })

        return Response({'days': days})