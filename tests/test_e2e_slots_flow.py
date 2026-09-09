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


async def test_register_then_spin_updates_balance_consistently(client):
    register_resp = await _register(client, username="e2e_player", email="e2e_player@example.com")
    assert register_resp.status_code == 200  # httpx follows the 303 redirect by default
    assert "1000 ₴" in register_resp.text

    slots_page = await client.get("/games/slots")
    assert slots_page.status_code == 200
    csrf2 = await _csrf_from(slots_page.text)

    spin_resp = await client.post("/games/slots/spin", data={"bet": "50", "csrf_token": csrf2})
    assert spin_resp.status_code == 200

    data = spin_resp.json()
    assert len(data["reels"]) == 3
    assert data["bet"] == 50
    assert data["balance"] == 1000 - 50 + data["winnings"]


async def test_spin_below_minimum_bet_is_rejected(client):
    await _register(client, username="e2e_lowbet", email="e2e_lowbet@example.com")

    slots_page = await client.get("/games/slots")
    csrf2 = await _csrf_from(slots_page.text)

    resp = await client.post("/games/slots/spin", data={"bet": "1", "csrf_token": csrf2})
    assert resp.status_code == 400
    assert "Bet must be between" in resp.json()["error"]


async def test_spin_without_csrf_token_is_rejected(client):
    await _register(client, username="e2e_nocsrf", email="e2e_nocsrf@example.com")

    resp = await client.post("/games/slots/spin", data={"bet": "50"})
    assert resp.status_code == 403


async def test_spin_requires_login(client):
    # CSRF check runs before the auth check for this route, so an anonymous
    # request with no CSRF cookie at all is rejected at 403 (covered by
    # test_spin_without_csrf_token_is_rejected). This test instead isolates
    # the auth gate itself: a real CSRF cookie, but no logged-in session.
    login_page = await client.get("/login")
    assert CSRF_RE.search(login_page.text), "expected a csrf_token even for anonymous visitors"
    cookie_token = client.cookies.get("csrf_token")

    resp = await client.post("/games/slots/spin", data={"bet": "50", "csrf_token": cookie_token})
    assert resp.status_code == 401
    assert resp.json()["error"] == "Authentication required"


async def test_slots_page_requires_login(client):
    resp = await client.get("/games/slots")
    assert resp.status_code == 200
    assert resp.url.path == "/login"


async def test_slots_page_keeps_site_chrome_and_frame_options(client):
    await _register(client, username="e2e_frame_opts", email="e2e_frame_opts@example.com")
    resp = await client.get("/games/slots")
    assert resp.status_code == 200
    # The colorful "arcade" game box lives inside the normal page, with the
    # site's own header/nav still present around it — not a separate
    # embed/iframe document.
    assert 'id="main-nav"' in resp.text
    assert 'id="slot-form"' in resp.text
    assert resp.headers["x-frame-options"] == "DENY"


async def test_register_rejects_mismatched_passwords(client):
    register_page = await client.get("/register")
    csrf = await _csrf_from(register_page.text)

    resp = await client.post(
        "/auth/register",
        data={
            "username": "e2e_mismatch",
            "email": "e2e_mismatch@example.com",
            "password": "SuperSecret123",
            "password_confirm": "SuperSecret124",
            "csrf_token": csrf,
        },
    )
    assert resp.status_code == 400
    assert "Passwords do not match" in resp.text
