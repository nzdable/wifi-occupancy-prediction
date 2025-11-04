from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsRoleAdmin(BasePermission):
    """
    Allow if user.is_staff OR user.role.lower() == 'admin'.
    """
    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        role = (getattr(u, "role", "") or "").strip().lower()
        return bool(u.is_staff or role == "admin")
