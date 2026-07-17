from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsNotBlocked(BasePermission):
    message = "Аккаунт заблокирован."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True
        return not getattr(user, "is_blocked", False)


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.id
