from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services import account_service
from app.services.account_service import AccountError, MAX_DEPOSIT, MAX_WITHDRAWAL, MIN_DEPOSIT, MIN_WITHDRAWAL
from app.services.auth_service import require_user
from app.services.csrf import get_or_create_csrf_token, set_csrf_cookie, verify_csrf
from app.services.wallet_service import get_wallet
from app.templating import templates

router = APIRouter(prefix="/account")


async def _render(request: Request, db: AsyncSession, user: User, *, message: str | None = None, error: str | None = None, status_code: int = 200):
    wallet = await get_wallet(db, user.id)
    transactions = await account_service.recent_transactions(db, user.id)
    token, is_new = get_or_create_csrf_token(request)

    response = templates.TemplateResponse(
        request,
        "account.html",
        {
            "user": user,
            "wallet": wallet,
            "transactions": transactions,
            "csrf_token": token,
            "message": message,
            "error": error,
            "min_deposit": MIN_DEPOSIT,
            "max_deposit": MAX_DEPOSIT,
            "min_withdrawal": MIN_WITHDRAWAL,
            "max_withdrawal": MAX_WITHDRAWAL,
        },
        status_code=status_code,
    )
    if is_new:
        set_csrf_cookie(response, token)
    return response


@router.get("")
async def account_page(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(require_user)):
    return await _render(request, db, user)


@router.post("/deposit", dependencies=[Depends(verify_csrf)])
async def account_deposit(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
    amount: int = Form(...),
):
    try:
        outcome = await account_service.deposit(db, user_id=user.id, amount=amount)
    except AccountError as exc:
        return await _render(request, db, user, error=str(exc), status_code=400)

    return await _render(request, db, user, message=f"Deposited {outcome.amount} ₴")


@router.post("/withdraw", dependencies=[Depends(verify_csrf)])
async def account_withdraw(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
    amount: int = Form(...),
):
    try:
        outcome = await account_service.withdraw(db, user_id=user.id, amount=amount)
    except AccountError as exc:
        return await _render(request, db, user, error=str(exc), status_code=400)

    return await _render(request, db, user, message=f"Withdrew {outcome.amount} ₴")
