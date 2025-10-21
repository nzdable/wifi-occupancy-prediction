# users/signals.py

from allauth.account.signals import user_logged_in, user_signed_up
from allauth.exceptions import ImmediateHttpResponse
from django.dispatch import receiver
from django.contrib.auth import logout
from django.conf import settings
from django.http import HttpResponseRedirect


@receiver(user_signed_up)
def restrict_signup_domain(sender, request, user, **kwargs):
    """
    Runs during social signup. If the email is not AdDU, delete the just-created
    user and abort the auth flow with an immediate redirect back to the frontend.
    """
    email = (user.email or "").strip().lower()
    if not email.endswith("@addu.edu.ph"):
        # Remove the accidental signup row and stop the flow.
        try:
            user.delete()
        except Exception:
            pass

        logout(request)
        request.session.flush()
        resp = HttpResponseRedirect(f"{settings.FRONTEND_URL}/?error=invalid_email")
        raise ImmediateHttpResponse(resp)

    # Enrich the user from the social account (if present)
    social = user.socialaccount_set.first()
    if social and isinstance(getattr(social, "extra_data", None), dict):
        user.name = social.extra_data.get("name", "") or getattr(user, "name", "")

    # Set defaults (custom fields in your User model)
    if not getattr(user, "role", None):
        user.role = "student"
    user.status = "active"

    # Persist any changes made above
    user.save(update_fields=["name", "role", "status"])


@receiver(user_logged_in)
def restrict_login_domain(sender, request, user, **kwargs):
    """
    Runs on login. If the domain is invalid or the account is inactive,
    log the user out and abort with an immediate redirect.
    """
    email = (user.email or "").strip().lower()

    if not email.endswith("@addu.edu.ph"):
        logout(request)
        request.session.flush()
        resp = HttpResponseRedirect(f"{settings.FRONTEND_URL}/?error=invalid_email")
        raise ImmediateHttpResponse(resp)

    if getattr(user, "status", "active") != "active":
        logout(request)
        request.session.flush()
        resp = HttpResponseRedirect(f"{settings.FRONTEND_URL}/?error=inactive_account")
        raise ImmediateHttpResponse(resp)
