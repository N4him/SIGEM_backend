from django.urls import path
from .views import CheckInView, CheckOutView, MyRecordsView, WeeklySummaryView

urlpatterns = [
    path('checkin/', CheckInView.as_view(), name='attendance-checkin'),
    path('checkout/', CheckOutView.as_view(), name='attendance-checkout'),
    path('my-records/', MyRecordsView.as_view(), name='attendance-my-records'),
    path('weekly-summary/', WeeklySummaryView.as_view(), name='attendance-weekly'),
]