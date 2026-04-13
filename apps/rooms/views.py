from rest_framework import generics
from core.permissions import IsMonitorOrAdmin
from .models import Room
from .serializers import RoomSerializer


class RoomListView(generics.ListAPIView):
    permission_classes = [IsMonitorOrAdmin]
    serializer_class = RoomSerializer

    def get_queryset(self):
        return Room.objects.filter(is_active=True)