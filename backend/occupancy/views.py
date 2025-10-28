from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from . import models
from .serializers import SignalSerializer, ForecastSerializer, LibrarySerializer
from .permissions import IsAdminOrReadOnly  

class LibraryViewSet(viewsets.ModelViewSet):
    """
    CRUD for Library. Uses slug 'key' as lookup for clean URLs.
    """
    queryset = models.Library.objects.all().order_by("key")
    serializer_class = LibrarySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "key"                         # /libraries/<key>/
    lookup_value_regex = r"[-\w]+"
    filter_backends = [filters.SearchFilter]
    search_fields = ["key", "name"]

class SignalViewSet(viewsets.ModelViewSet):
    """
    CRUD for Signal. Supports filtering by library key.
    """
    queryset = models.Signal.objects.select_related("library").all().order_by("-ts")
    serializer_class = SignalSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["library__key", "library"]

class ForecastViewSet(viewsets.ModelViewSet):
    """
    CRUD for Forecast. Filter by library, version, family, horizon.
    """
    queryset = models.Forecast.objects.select_related("library").all().order_by("-ts")
    serializer_class = ForecastSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["library__key", "model_version", "model_family", "horizon_min"]