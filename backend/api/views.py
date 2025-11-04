from django.http import JsonResponse
from occupancy.models import Library
from occupancy.services import predict_latest_from_db
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
import numpy as np
import pandas as pd

from occupancy.models import Library
from occupancy.infer import get_series_df, load_artifacts_cached, one_step

DEFAULT_FAMILY = os.getenv("MODEL_DEFAULT_FAMILY", "cnn-lstm-attn")

def health(request):
    return JsonResponse({"status": "ok"}, status=200)

def predict_debug(request):
    lib_key = request.GET.get("library", "").strip()
    family  = request.GET.get("family", DEFAULT_FAMILY).strip()

    if not lib_key:
        return JsonResponse({"ok": False, "error": "Missing 'library'."}, status=400)

    if not Library.objects.filter(key=lib_key).exists():
        return JsonResponse({"ok": False, "error": f"Unknown library '{lib_key}'."}, status=404)
    
    

    res = predict_latest_from_db(lib_key, family)
    return JsonResponse(res, status=200 if res.get("ok") else 428)

class DebugSeedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lib_key = request.query_params.get("library", "").strip()
        family  = request.query_params.get("family", "cnn").strip()
        version = request.query_params.get("version", "v1").strip()
        hours   = int(request.query_params.get("hours", "48"))  # inspect last 48 by default

        lib = get_object_or_404(Library, key=lib_key)
        model, scaler, window, meta = load_artifacts_cached(family, lib.key, version)

        s = get_series_df(lib, hours=max(window, hours))
        tail = s.values[-window:].astype(float) if len(s) >= window else s.values.astype(float)

        # Try a single-step prediction using this seed
        yhat = (one_step(model, scaler, window, tail[-window:]) if len(tail) >= window else None)

        return Response({
            "library": lib.key,
            "family": family,
            "version": version,
            "window": int(window),
            "series_end": (s.index[-1].isoformat() if len(s) else None),
            "series_len": int(len(s)),
            "seed_len": int(len(tail)),
            "seed_minmax": (float(np.min(tail)) if len(tail) else None,
                            float(np.max(tail)) if len(tail) else None),
            "seed_sample": [float(x) for x in tail[-10:]] if len(tail) else [],
            "one_step_yhat": (float(yhat) if yhat is not None else None),
        }, status=200)
