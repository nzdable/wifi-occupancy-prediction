from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, mixins, status
from rest_framework.permissions import AllowAny
from . import models
from . import serializers
from .permissions import IsAdminOrReadOnly
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action


class LibraryViewSet(viewsets.ModelViewSet):
    """
    CRUD for Library. Uses slug 'key' as lookup for clean URLs.
    """
    queryset = models.Library.objects.all().order_by("key")
    serializer_class = serializers.LibrarySerializer
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
    serializer_class = serializers.SignalSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["library__key", "library"]

    def bulk_delete(self, request):
        """
        Delete all signals, or optionally all signals for a given library.
        Example:
            DELETE /signals/bulk_delete/
            DELETE /signals/bulk_delete/?library__key=rizal_library
        """
        library_key = request.query_params.get("library__key")
        qs = self.get_queryset()

        if library_key:
            qs = qs.filter(library__key=library_key)

        count = qs.count()
        if count == 0:
            return Response(
                {"detail": "No signals found to delete."},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted, _ = qs.delete()
        return Response(
            {"ok": True, "deleted_records": deleted, "library": library_key or "all"},
            status=status.HTTP_200_OK,
        )

class ForecastViewSet(viewsets.ModelViewSet):
    """
    CRUD for Forecast. Filter by library, version, family, horizon.
    """
    queryset = models.Forecast.objects.select_related("library").all().order_by("-ts")
    serializer_class = serializers.ForecastSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["library__key", "model_version", "model_family", "horizon_min"]

class ModelCandidateViewSet(viewsets.ModelViewSet):
    queryset = models.ModelCandidate.objects.select_related("library").all()
    serializer_class = serializers.ModelCandidateSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["library__key","family","version"]

    @action(detail=True, methods=["get","post"], url_path="evaluations")
    def evaluations(self, request, pk=None):
        cand = self.get_object()
        if request.method.lower() == "get":
            qs = cand.evaluations.order_by("-evaluated_at")
            return Response(ModelEvaluationSerializer(qs, many=True).data)
        ser = ModelEvaluationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(candidate=cand)
        return Response(ser.data, status=status.HTTP_201_CREATED)

class ActiveModelViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = models.ActiveModel.objects.select_related("library","candidate")
    serializer_class = serializers.ActiveModelSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "library__key"   # /active/<library_key> if you mount it like that

    # Convenience: set by library_key
    @action(detail=False, methods=["put"], url_path=r"libraries/(?P<library_key>[-\w]+)/active")
    def set_active(self, request, library_key=None):
        lib = get_object_or_404(models.Library, key=library_key)
        cand_id = request.data.get("candidate_id")
        cand = get_object_or_404(models.ModelCandidate, id=cand_id, library=lib)

        obj, _ = models.ActiveModel.objects.update_or_create(
            library=lib,
            defaults={
                "candidate": cand,
                "selected_by": request.data.get("selected_by","manual"),
                "criterion": request.data.get("criterion","rmse_min"),
            }
        )
        return Response(serializers.ActiveModelSerializer(obj).data, status=200)