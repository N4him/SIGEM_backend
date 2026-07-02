import csv
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from core.permissions import IsAdmin
from .models import CustomUser
from .serializers import UserAdminSerializer, RegisterSerializer
from apps.attendance.models import AttendanceRecord
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class UserListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserAdminSerializer

    def get_queryset(self):
        return CustomUser.objects.filter(
            role=CustomUser.Role.MONITOR
        ).order_by('first_name')


class UserCreateView(generics.CreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # Validar contraseña primero
        try:
            validate_password(request.data.get('password'))
        except ValidationError as e:
            return Response({'errors': e.messages}, status=status.HTTP_400_BAD_REQUEST)

        # Luego continuar con el flujo normal
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'success': True, 'user': UserAdminSerializer(user).data},
            status=status.HTTP_201_CREATED
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserAdminSerializer
    queryset = CustomUser.objects.filter(role=CustomUser.Role.MONITOR)
    http_method_names = ['get', 'patch', 'delete']

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserAdminSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'user': serializer.data})

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


class UserToggleView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk, role=CustomUser.Role.MONITOR)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        user.is_active = not user.is_active
        user.save()
        return Response({'success': True, 'is_active': user.is_active})


class ReportsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        print(f"[Reports] Llegó petición — params: {request.query_params}")
        export_format = request.query_params.get('export', 'json')
        filter_type = request.query_params.get('filter', 'all')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        room_id = request.query_params.get('room_id')
        user_id = request.query_params.get('user_id')

        records = AttendanceRecord.objects.select_related('user', 'room').filter(
            status=AttendanceRecord.Status.CLOSED
        ).order_by('-check_in')

        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()

        if filter_type == 'weekly':
            start = now - timedelta(days=7)
            records = records.filter(check_in__gte=start)
        elif filter_type == 'monthly':
            start = now - timedelta(days=30)
            records = records.filter(check_in__gte=start)
        elif filter_type == 'custom' and from_date and to_date:
            records = records.filter(
                check_in__date__gte=from_date,
                check_in__date__lte=to_date
            )

        if room_id:
            records = records.filter(room_id=room_id)
        if user_id:
            records = records.filter(user_id=user_id)

        if export_format == 'csv':
            return self._export_csv(records)

        data = [
            {
                'id': str(r.id),
                'monitor': r.user.get_full_name(),
                'email': r.user.email,
                'sala': r.room.name,
                'fecha': timezone.localtime(r.check_in).date().isoformat(),
                'entrada': timezone.localtime(r.check_in).strftime('%H:%M'),
                'salida': timezone.localtime(r.check_out).strftime('%H:%M') if r.check_out else '',
                'horas': r.hours_worked or 0,
                'foto': r.photo_url,
            }
            for r in records
        ]

        total_horas = sum(r['horas'] for r in data)

        return Response({
            'success': True,
            'records': data,
            'total': len(data),
            'total_horas': round(total_horas, 2),
        })

    def _export_csv(self, records):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.csv"'
        writer = csv.writer(response)
        writer.writerow(['Monitor', 'Email', 'Sala', 'Fecha', 'Entrada', 'Salida', 'Horas'])
        from django.utils import timezone
        for r in records:
            writer.writerow([
                r.user.get_full_name(),
                r.user.email,
                r.room.name,
                timezone.localtime(r.check_in).date().isoformat(),
                timezone.localtime(r.check_in).strftime('%H:%M'),
                timezone.localtime(r.check_out).strftime('%H:%M') if r.check_out else '',
                r.hours_worked or 0,
            ])
        return response
    
class FilterOptionsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.rooms.models import Room
        rooms = Room.objects.filter(is_active=True).values('id', 'name')
        monitors = CustomUser.objects.filter(
            role=CustomUser.Role.MONITOR
        ).values('id', 'first_name', 'last_name')

        return Response({
            'rooms': list(rooms),
            'monitors': [
                {
                    'id': str(m['id']),
                    'name': f"{m['first_name']} {m['last_name']}"
                }
                for m in monitors
            ]
        })