from django.urls import path
from .admin_views import (
    UserListView, UserCreateView, UserDetailView,
    UserToggleView, ReportsView, FilterOptionsView
)

urlpatterns = [
    path('users/', UserListView.as_view(), name='admin-users'),
    path('reports/filters/', FilterOptionsView.as_view(), name='admin-filters'),
    path('users/create/', UserCreateView.as_view(), name='admin-users-create'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='admin-user-detail'),
    path('users/<uuid:pk>/toggle/', UserToggleView.as_view(), name='admin-user-toggle'),
    path('reports/', ReportsView.as_view(), name='admin-reports'),
]