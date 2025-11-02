# users/views_admin.py
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import CustomUser
from .serializers import UserListSerializer
from .permissions import IsRoleAdmin


class TenPerPage(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminUserList(generics.ListAPIView):
    """
    GET /users/admin/manage/?q=foo&page=1&page_size=10
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsRoleAdmin]
    pagination_class = TenPerPage

    def get_queryset(self):
        # Tell Pylance this is a DRF Request (has .query_params)
        req: Request = self.request  # type: ignore[assignment]
        q = (getattr(req, "query_params", self.request.GET).get("q") or "").strip()

        qs = CustomUser.objects.all().order_by("email")
        if q:
            qs = qs.filter(
                Q(email__icontains=q) |
                Q(name__icontains=q) |
                Q(role__icontains=q)
            )
        return qs


class AdminUserRoleUpdate(generics.UpdateAPIView):
    """
    PATCH /users/admin/manage/<id>/
    body: {"role":"admin"} or {"role":"student"}
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsRoleAdmin]
    queryset = CustomUser.objects.all()
    http_method_names = ["patch"]

    def patch(self, request: Request, *args, **kwargs):
        # prevent demoting/changing your own role
        target = self.get_object()
        if request.user.id == target.id:
            return Response({"detail": "You cannot change your own role."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().patch(request, *args, **kwargs)