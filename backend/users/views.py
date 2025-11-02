from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token

@login_required
def admin_site(request):
    user = request.user
    if user.role != "admin":
        return JsonResponse({"error": "Access denied"}, status=403)
    
    return JsonResponse({
        "message": "Welcome to the admin site!",
        "user": user.email,
        "role": user.role,
    })

@ensure_csrf_cookie
def whoami(request):
    if request.user.is_authenticated:
        user = request.user
        return JsonResponse({
            "authenticated": True,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "status": user.status,
        })
    return JsonResponse({"authenticated": False})

@login_required
def role_redirect(request):
    role = (request.user.role or "").strip().lower()
    if role == "admin":
        return redirect(f"{settings.FRONTEND_URL}/admin")
    return redirect(f"{settings.FRONTEND_URL}/Student")

@ensure_csrf_cookie        # sets the csrftoken cookie on 8000
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})