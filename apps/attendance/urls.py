from django.urls import path
from .views import CheckInView, CheckOutView, MyRecordsView

urlpatterns = [
    path('checkin/', CheckInView.as_view(), name='attendance-checkin'),
    path('checkout/', CheckOutView.as_view(), name='attendance-checkout'),
    path('my-records/', MyRecordsView.as_view(), name='attendance-my-records'),
]