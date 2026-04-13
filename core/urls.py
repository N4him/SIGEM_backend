from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/auth/', include('apps.users.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/rooms/', include('apps.rooms.urls')),
    path('api/admin/', include('apps.users.admin_urls')),
    path('admin/', admin.site.urls),
] + static('/media/', document_root=settings.BASE_DIR / 'media')