from .auth import request_user


def current_legacy_user(request):
    return {"current_user": request_user(request)}
