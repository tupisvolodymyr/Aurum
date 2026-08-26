from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.games.wheel import MULTIPLIERS as WHEEL_MULTIPLIERS
from app.models import Game, User
from app.services import catalog_service
from app.services.auth_service import get_current_user, require_user
from app.services.csrf import get_or_create_csrf_token, set_csrf_cookie, verify_csrf
from app.services.slots_service import MAX_BET, MIN_BET, SpinError, spin
from app.services.wallet_service import get_wallet
from app.services.wheel_service import MAX_BET as WHEEL_MAX_BET
from app.services.wheel_service import MIN_BET as WHEEL_MIN_BET
from app.services.wheel_service import WheelSpinError
from app.services.wheel_service import spin as wheel_spin
from app.templating import templates

router = APIRouter(prefix="/games")


async def _get_game_or_404(db: AsyncSession, slug: str) -> Game:
    result = await db.execute(select(Game).where(Game.slug == slug))
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.get("/slots")
async def slots_page(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    wallet = await get_wallet(db, user.id)

    game = await _get_game_or_404(db, "slots")
    await catalog_service.record_recently_played(db, user_id=user.id, game_id=game.id)

    token, is_new = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "games/slots.html",
        {"user": user, "wallet": wallet, "csrf_token": token, "min_bet": MIN_BET, "max_bet": MAX_BET},
    )
    if is_new:
        set_csrf_cookie(response, token)
    return response


@router.post("/slots/spin", dependencies=[Depends(verify_csrf)])
async def slots_spin(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
    bet: int = Form(...),
):
    # Plain 401 JSON rather than require_user's login-redirect: this is a
    # fetch() call driving the reel animation client-side, not a page nav.
    if user is None:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    game = await _get_game_or_404(db, "slots")

    try:
        outcome = await spin(db, user_id=user.id, bet=bet, game_id=game.id)
    except SpinError as exc:
        wallet = await get_wallet(db, user.id)
        return JSONResponse({"error": str(exc), "balance": wallet.balance}, status_code=400)

    return JSONResponse(
        {
            "reels": [symbol.value for symbol in outcome.result.reels],
            "multiplier": outcome.result.multiplier,
            "winnings": outcome.winnings,
            "bet": bet,
            "balance": outcome.balance,
        }
    )


@router.get("/golden-wheel")
async def wheel_page(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    wallet = await get_wallet(db, user.id)

    game = await _get_game_or_404(db, "golden-wheel")
    await catalog_service.record_recently_played(db, user_id=user.id, game_id=game.id)

    token, is_new = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        request,
        "games/wheel.html",
        {
            "user": user,
            "wallet": wallet,
            "csrf_token": token,
            "min_bet": WHEEL_MIN_BET,
            "max_bet": WHEEL_MAX_BET,
            "multipliers": WHEEL_MULTIPLIERS,
        },
    )
    if is_new:
        set_csrf_cookie(response, token)
    return response


@router.post("/golden-wheel/spin", dependencies=[Depends(verify_csrf)])
async def wheel_spin_route(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
    bet: int = Form(...),
    multiplier: int = Form(...),
):
    # Plain 401 JSON rather than require_user's login-redirect: this is a
    # fetch() call driving the wheel animation client-side, not a page nav.
    if user is None:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    game = await _get_game_or_404(db, "golden-wheel")

    try:
        outcome = await wheel_spin(db, user_id=user.id, bet=bet, chosen_multiplier=multiplier, game_id=game.id)
    except WheelSpinError as exc:
        wallet = await get_wallet(db, user.id)
        return JSONResponse({"error": str(exc), "balance": wallet.balance}, status_code=400)

    return JSONResponse(
        {
            "landed_multiplier": outcome.landed_multiplier,
            "chosen_multiplier": outcome.chosen_multiplier,
            "winnings": outcome.winnings,
            "bet": bet,
            "balance": outcome.balance,
        }
    )


@router.post("/{slug}/favorite", dependencies=[Depends(verify_csrf)])
async def toggle_favorite(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    # Plain 401 JSON rather than require_user's login-redirect: this is a
    # fetch() call from app.js, which handles the unauthenticated case by
    # opening the auth modal itself rather than following a redirect.
    if user is None:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    game = await _get_game_or_404(db, slug)
    favorited = await catalog_service.toggle_favorite(db, user_id=user.id, game_id=game.id)
    return JSONResponse({"favorited": favorited})
