from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

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