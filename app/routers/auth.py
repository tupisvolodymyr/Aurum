from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.auth import LoginForm, RegisterForm
from app.services.auth_service import AuthError, authenticate_user, create_session, register_user, revoke_session
from app.services.csrf import get_or_create_csrf_token, set_csrf_cookie, verify_csrf
from app.services.redirects import safe_next_path
from app.templating import templates

router = APIRouter(prefix="/auth")
settings = get_settings()

_VALUE_ERROR_PREFIX = "Value error, "


def _first_error_message(exc: ValidationError) -> str:
    msg = exc.errors()[0]["msg"]
    return msg.removeprefix(_VALUE_ERROR_PREFIX)


def _set_session_cookie(response: RedirectResponse, raw_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_seconds,
        path="/",
    )


@router.post("/register", dependencies=[Depends(verify_csrf)])
async def register(
    request: Request,
    db: AsyncSession = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    next: str | None = Form(None),
):
    next_path = safe_next_path(next)

    def render_error(message: str):
        token, is_new = get_or_create_csrf_token(request)
        resp = templates.TemplateResponse(
            request, "register.html", {"csrf_token": token, "error": message, "next": next_path}, status_code=400
        )
        if is_new:
            set_csrf_cookie(resp, token)
        return resp

    try:
        data = RegisterForm(username=username, email=email, password=password, password_confirm=password_confirm)
    except ValidationError as exc:
        return render_error(_first_error_message(exc))

    try:
        user = await register_user(db, username=data.username, email=data.email, password=data.password)
    except AuthError as exc:
        return render_error(str(exc))

    raw_token = await create_session(
        db, user=user, user_agent=request.headers.get("user-agent"), ip_address=request.client.host if request.client else None
    )
    response = RedirectResponse(url=next_path or "/", status_code=303)
    _set_session_cookie(response, raw_token)
    return response


@router.post("/login", dependencies=[Depends(verify_csrf)])
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    identifier: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
):
    next_path = safe_next_path(next)

    def render_error(message: str):
        token, is_new = get_or_create_csrf_token(request)
        resp = templates.TemplateResponse(
            request, "login.html", {"csrf_token": token, "error": message, "next": next_path}, status_code=400
        )
        if is_new:
            set_csrf_cookie(resp, token)
        return resp

    try:
        data = LoginForm(identifier=identifier, password=password)
    except ValidationError:
        return render_error("Invalid username/email or password")

    try:
        user = await authenticate_user(db, identifier=data.identifier, password=data.password)
    except AuthError as exc:
        return render_error(str(exc))

    raw_token = await create_session(
        db, user=user, user_agent=request.headers.get("user-agent"), ip_address=request.client.host if request.client else None
    )
    response = RedirectResponse(url=next_path or "/", status_code=303)
    _set_session_cookie(response, raw_token)
    return response


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        await revoke_session(db, raw_token)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response
