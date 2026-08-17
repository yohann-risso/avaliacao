from __future__ import annotations

import hashlib
import hmac
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import LegacyLoginUser


def verify_legacy_password(password: str, stored_hash: str) -> bool:
    """Verify the PBKDF2 format already used by login_users."""
    try:
        algorithm, iterations, salt_hex, digest_hex = str(stored_hash or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", str(password or "").encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (TypeError, ValueError):
        return False


def request_user(request) -> LegacyLoginUser | None:
    user_id = request.session.get("legacy_user_id")
    if not user_id:
        return None
    return LegacyLoginUser.objects.filter(id=user_id, active=True).first()


def login_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request_user(request):
            messages.info(request, "Faça login para acessar o sistema.")
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request_user(request).is_admin:
            messages.error(request, "Acesso restrito a administradores.")
            return redirect("dashboard")
        return view(request, *args, **kwargs)
    return wrapped
