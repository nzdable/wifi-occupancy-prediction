# occupancy/views_models.py
from pathlib import Path
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from typing import cast
import json

from .models import Library, ModelCandidate, ActiveModel
from .serializers import ModelCandidateSerializer, ActiveModelSerializer
from .utils.artifacts import read_meta_version
from .views_forecast import FAMILIES

ARTIFACTS_ROOT = Path(settings.BASE_DIR) / "artifacts"

class CandidatesView(APIView):
    permission_classes = [AllowAny]  # or IsAdminUser if you prefer

    def get(self, request):
        lib_key = (request.query_params.get("library") or "").strip()
        if not lib_key:
            return Response({"detail": "library is required"}, status=400)
        lib = get_object_or_404(Library, key=lib_key)
        qs = ModelCandidate.objects.filter(library=lib).order_by("family", "version")
        return Response(ModelCandidateSerializer(qs, many=True).data)


class ActivePerLibraryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lib_key = (request.query_params.get("library") or "").strip()
        if not lib_key:
            return Response({"detail": "library is required"}, status=400)
        lib = get_object_or_404(Library, key=lib_key)
        try:
            active = ActiveModel.objects.select_related("candidate").get(library=lib)
            return Response(ActiveModelSerializer(active).data)
        except ActiveModel.DoesNotExist:
            return Response({"detail": "No active model for this library."}, status=404)

    def put(self, request):
        # body: { library: "gisbert_2nd_floor", family: "...", version: "..." }
        lib_key = (request.data.get("library") or "").strip()
        family  = (request.data.get("family") or "").strip()
        version = (request.data.get("version") or "").strip()
        if not (lib_key and family and version):
            return Response({"detail": "library, family, and version are required"}, status=400)

        lib = get_object_or_404(Library, key=lib_key)

        # ensure candidate exists (create if missing)
        cand, _ = ModelCandidate.objects.get_or_create(
            library=lib, family=family, version=version
        )

        # upsert ActiveModel
        with transaction.atomic():
            active, created = ActiveModel.objects.select_for_update().get_or_create(
                library=lib, defaults={"candidate": cand}
            )
            if not created:
                active.candidate = cand
                active.save(update_fields=["candidate", "selected_by", "criterion"])
        return Response({"ok": True, "family": family, "version": version})

class SyncCandidatesView(APIView):
    permission_classes = [AllowAny] if settings.DEBUG else [IsAdminUser]

    def post(self, request):
        created = 0
        for lib in Library.objects.all():
            for family_dir in ARTIFACTS_ROOT.iterdir():
                if not family_dir.is_dir():
                    continue
                family = family_dir.name
                if family not in FAMILIES:
                    continue  # skip stray folders

                lib_dir = family_dir / lib.key
                if not lib_dir.exists():
                    continue

                families = []
                meta_p = lib_dir / "meta.json"

                # Flat layout: artifacts/<family>/<lib_key>/*
                if (lib_dir / "model.keras").exists() or meta_p.exists():
                    # Prefer meta.json’s version if present
                    try:
                        ver = read_meta_version(family, lib.key) or "v1"
                    except Exception:
                        ver = "v1"
                    families.append((family, str(ver), lib_dir))
                else:
                    # Versioned subfolders: artifacts/<family>/<lib_key>/<version>/*
                    for version_dir in lib_dir.iterdir():
                        if version_dir.is_dir() and (
                            (version_dir / "model.keras").exists() or
                            (version_dir / "meta.json").exists()
                        ):
                            families.append((family, version_dir.name, version_dir))

                for fam, ver, _p in families:
                    _, made = ModelCandidate.objects.get_or_create(
                        library=lib, family=fam, version=str(ver)
                    )
                    created += int(made)

        return Response({"ok": True, "created": created})

class ModelCandidatesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lib_key = request.query_params.get("library", "").strip()
        if not lib_key:
            return Response({"detail": "Missing library"}, status=400)

        lib = get_object_or_404(Library, key=lib_key)

        out = []
        for fam in sorted(FAMILIES):
            ver = read_meta_version(fam, lib.key)
            if not ver:
                continue
            ver = str(ver)  # ensure string like "1.1"
            # upsert (optional but recommended so Admin UI stays consistent)
            obj, _ = ModelCandidate.objects.get_or_create(
                library=lib, family=fam, version=ver
            )

            obj = cast(ModelCandidate, obj)

            out.append({
                "id": obj.pk,
                "library_key": lib.key,
                "family": fam,
                "version": ver,  # <- exact from meta.json
            })
        return Response(out, status=200)
