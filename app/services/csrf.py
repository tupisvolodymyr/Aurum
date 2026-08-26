import secrets

from fastapi import HTTPException, Request, Response, status

from app.config import get_settings
from app.services.security import constant_time_compare

settings = get_settings()


def get_or_create_csrf_token(request: Request) -> tuple[str, bool]:
    """Double-submit cookie pattern: an httponly cookie holds the token,
    the same value must be echoed back in a hidden form field. A cross-site
    form can't read the httponly cookie, so it can't forge a matching field.

    Returns (token, is_new). Callers must set_csrf_cookie() on the actual
    response object when is_new is True (setting cookies on an injected
    Response dependency has no effect once the handler returns its own
    Response/TemplateResponse instance).
    """
    token = request.cookies.get(settings.csrf_cookie_name)
    if token:
        return token, False
    return secrets.token_urlsafe(32), True


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_seconds,
    )


async def verify_csrf(request: Request) -> None:
    """Accepts the token from a form field (regular POSTs) or an
    X-CSRF-Token header (fetch/AJAX calls, which read it from the
    <meta name="csrf-token"> tag base.html renders into every page).
    """
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    submitted = request.headers.get("x-csrf-token")
    if submitted is None:
        form = await request.form()
        submitted = form.get("csrf_token")

    if not submitted or not cookie_token or not constant_time_compare(str(submitted), cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
