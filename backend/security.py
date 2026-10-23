import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from functools import wraps

from flask import current_app, g, redirect, request, session, url_for

from backend.errors import AppError

ROLES = ("student", "counsellor", "admin")


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload_b64: str) -> str:
    key = current_app.config["SECRET_KEY"].encode()
    return _b64(hmac.new(key, payload_b64.encode(), hashlib.sha256).digest())


def issue_token(user_id, role, ttl=None):
    ttl = ttl or current_app.config["API_TOKEN_TTL"]
    payload = {"sub": user_id, "role": role,
               "iat": int(time.time()), "exp": int(time.time()) + ttl}
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{payload_b64}.{_sign(payload_b64)}", payload["exp"]


def verify_token(token):
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        payload = json.loads(_unb64(payload_b64))
    except Exception:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def load_current_user():
    from backend.repositories import user_repo

    g.current_user = None
    g.user = None
    g.auth_method = None

    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        payload = verify_token(header[7:].strip())
        if payload:
            user = user_repo.get_by_id(payload["sub"])
            if user and user["is_active"]:
                g.current_user = g.user = dict(user)
                g.auth_method = "token"
                return

    if "user_id" in session:
        g.current_user = g.user = {
            "user_id": session["user_id"],
            "username": session["username"],
            "role": session["role"],
            "student_id": session.get("student_id"),
            "counsellor_id": session.get("counsellor_id"),
            "display_name": session.get("display_name"),
        }
        g.auth_method = "session"


def current_user():
    return getattr(g, "current_user", None)


def is_staff():
    user = current_user()
    return bool(user and user["role"] in ("counsellor", "admin"))


def login_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                if request.path.startswith(current_app.config["API_PREFIX"]):
                    raise AppError("Authentication required.", 401)
                return redirect(url_for("auth.login", next=request.full_path))
            if roles and user["role"] not in roles:
                raise AppError("You do not have access to that resource.", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def api_login_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                raise AppError("Authentication required. Send an "
                               "Authorization: Bearer <token> header.", 401)
            if roles and user["role"] not in roles:
                raise AppError("Your role may not access this resource.", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def owns_student_or_staff(student_id):
    user = current_user()
    if user is None:
        raise AppError("Authentication required.", 401)
    if user["role"] == "student" and user.get("student_id") != student_id:
        raise AppError("You may only view your own records.", 403)
