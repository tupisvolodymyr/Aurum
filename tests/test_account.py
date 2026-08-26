import re

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]*)"')


async def _csrf_from(text: str) -> str:
    match = CSRF_RE.search(text)
    assert match, "csrf_token hidden field not found in response"
    return match.group(1)


async def _register(client, *, username: str, email: str, password: str = "SuperSecret123"):
    register_page = await client.get("/register")
    csrf = await _csrf_from(register_page.text)
    return await client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "password_confirm": password,
            "csrf_token": csrf,
        },
    )


async def test_account_page_requires_login(client):
    resp = await client.get("/account")
    assert resp.status_code == 200
    assert resp.url.path == "/login"
    assert "next=" in str(resp.url)


async def test_deposit_increases_balance_and_logs_transaction(client):
    await _register(client, username="acct_deposit", email="acct_deposit@example.com")

    account_page = await client.get("/account")
    assert "1000 ₴" in account_page.text
    csrf = await _csrf_from(account_page.text)

    resp = await client.post("/account/deposit", data={"amount": "200", "csrf_token": csrf})
    assert resp.status_code == 200
    assert "1200 ₴" in resp.text
    assert "Deposited 200" in resp.text
    assert "Deposit" in resp.text


async def test_withdraw_decreases_balance(client):
    await _register(client, username="acct_withdraw", email="acct_withdraw@example.com")

    account_page = await client.get("/account")
    csrf = await _csrf_from(account_page.text)

    resp = await client.post("/account/withdraw", data={"amount": "150", "csrf_token": csrf})
    assert resp.status_code == 200
    assert "850 ₴" in resp.text
    assert "Withdrew 150" in resp.text


async def test_withdraw_rejects_amount_above_balance(client):
    await _register(client, username="acct_overdraw", email="acct_overdraw@example.com")
    # starting balance is 1000; 1500 is within the [min, max] bounds but
    # exceeds what's actually in the wallet.
    account_page = await client.get("/account")
    csrf = await _csrf_from(account_page.text)

    resp = await client.post("/account/withdraw", data={"amount": "1500", "csrf_token": csrf})
    assert resp.status_code == 400
    assert "Insufficient balance" in resp.text


async def test_withdraw_rejects_amount_below_minimum(client):
    await _register(client, username="acct_toosmall", email="acct_toosmall@example.com")

    account_page = await client.get("/account")
    csrf = await _csrf_from(account_page.text)

    resp = await client.post("/account/withdraw", data={"amount": "5", "csrf_token": csrf})
    assert resp.status_code == 400
    assert "Withdrawal must be between" in resp.text


async def test_deposit_without_csrf_token_is_rejected(client):
    await _register(client, username="acct_nocsrf", email="acct_nocsrf@example.com")

    resp = await client.post("/account/deposit", data={"amount": "100"})
    assert resp.status_code == 403
