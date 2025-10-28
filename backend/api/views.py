from django.http import JsonResponse
from occupancy.models import Library
from occupancy.services import predict_latest_from_db
import os

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