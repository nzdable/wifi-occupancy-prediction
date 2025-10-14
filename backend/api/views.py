from django.http import JsonResponse
def ping(_request):
    return JsonResponse({"ok": True, "service": "django-backend"})