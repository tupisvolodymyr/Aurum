from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services import catalog_service
from app.services.auth_service import get_current_user
from app.services.csrf import get_or_create_csrf_token, set_csrf_cookie
from app.services.redirects import safe_next_path
from app.services.wallet_service import get_wallet
from app.templating import templates

router = APIRouter()


@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_current_user)):
    context = {
        "user": user,
        "games": await catalog_service.list_games(db),
        "winners": await catalog_service.latest_winners(db),
        "favorite_ids": set(),
        "recently_played": [],
        "recommended": [],
    }

    if user is not None:
        context["wallet"] = await get_wallet(db, user.id)
        context["favorite_ids"] = await catalog_service.favorite_game_ids(db, user.id)
        context["recently_played"] = await catalog_service.recently_played_games(db, user.id)
        context["recommended"] = await catalog_service.recommended_games(db, user.id)

    token, is_new = get_or_create_csrf_token(request)
    context["csrf_token"] = token
    response = templates.TemplateResponse(request, "index.html", context)
    if is_new:
        set_csrf_cookie(response, token)
    return response


@router.get("/login")
async def login_page(request: Request, user: User | None = Depends(get_current_user), next: str | None = Query(None)):
    next_path = safe_next_path(next)
    if user is not None:
        return RedirectResponse(url=next_path or "/", status_code=303)

    token, is_new = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(request, "login.html", {"csrf_token": token, "error": None, "next": next_path})
    if is_new:
        set_csrf_cookie(response, token)
    # Without this, the browser's back/forward cache can restore this page
    # byte-for-byte after a successful login/register — showing the stale
    # "logged out" form and letting the user resubmit the same username,
    # which then fails as "already taken" even though they're already in.
    # no-store forces a fresh server round-trip on back-navigation, so the
    # `if user is not None: redirect` check above actually runs again.
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/register")
async def register_page(request: Request, user: User | None = Depends(get_current_user), next: str | None = Query(None)):
    next_path = safe_next_path(next)
    if user is not None:
        return RedirectResponse(url=next_path or "/", status_code=303)

    token, is_new = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(request, "register.html", {"csrf_token": token, "error": None, "next": next_path})
    if is_new:
        set_csrf_cookie(response, token)
    # See the matching comment in login_page: prevents bfcache from showing
    # a stale pre-registration form on browser back-navigation.
    response.headers["Cache-Control"] = "no-store"
    return response
