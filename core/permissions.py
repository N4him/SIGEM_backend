from rest_framework.permissions import BasePermission


class IsMonitor(BasePermission):
    """Permite acceso solo a usuarios con rol monitor."""
    message = 'Solo los monitores pueden realizar esta acción.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_monitor
        )


class IsAdmin(BasePermission):
    """Permite acceso solo a usuarios con rol admin."""
    message = 'Solo los administradores pueden realizar esta acción.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_admin
        )


class IsMonitorOrAdmin(BasePermission):
    """Permite acceso a monitores y administradores."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
        )