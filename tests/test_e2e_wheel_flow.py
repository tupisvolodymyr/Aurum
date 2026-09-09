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


async def test_wheel_page_requires_login(client):
    resp = await client.get("/games/golden-wheel")
    assert resp.status_code == 200
    assert resp.url.path == "/login"
    assert "next=" in str(resp.url)


async def test_wheel_page_keeps_site_chrome_and_frame_options(client):
    await _register(client, username="e2e_wheel_frame_opts", email="e2e_wheel_frame_opts@example.com")
    resp = await client.get("/games/golden-wheel")
    assert resp.status_code == 200
    # The colorful "arcade" game box lives inside the normal page, with the
    # site's own header/nav still present around it — not a separate
    # embed/iframe document.
    assert 'id="main-nav"' in resp.text
    assert 'id="wheel-form"' in resp.text
    assert resp.headers["x-frame-options"] == "DENY"


async def test_register_then_wheel_spin_updates_balance_consistently(client):
    await _register(client, username="e2e_wheel_player", email="e2e_wheel_player@example.com")

    wheel_page = await client.get("/games/golden-wheel")
    assert wheel_page.status_code == 200
    assert "Golden Wheel" in wheel_page.text
    csrf = await _csrf_from(wheel_page.text)

    spin_resp = await client.post(
        "/games/golden-wheel/spin", data={"bet": "50", "multiplier": "2", "csrf_token": csrf}
    )
    assert spin_resp.status_code == 200

    data = spin_resp.json()
    assert data["landed_multiplier"] in (2, 5, 10, 20, 25, 50, 100)
    assert data["chosen_multiplier"] == 2
    assert data["balance"] == 1000 - 50 + data["winnings"]
    if data["landed_multiplier"] == 2:
        assert data["winnings"] == 100
    else:
        assert data["winnings"] == 0


async def test_wheel_spin_below_minimum_bet_is_rejected(client):
    await _register(client, username="e2e_wheel_lowbet", email="e2e_wheel_lowbet@example.com")

    wheel_page = await client.get("/games/golden-wheel")
    csrf = await _csrf_from(wheel_page.text)

    resp = await client.post("/games/golden-wheel/spin", data={"bet": "1", "multiplier": "2", "csrf_token": csrf})
    assert resp.status_code == 400
    assert "Bet must be between" in resp.json()["error"]


async def test_wheel_spin_rejects_invalid_multiplier(client):
    await _register(client, username="e2e_wheel_badpick", email="e2e_wheel_badpick@example.com")

    wheel_page = await client.get("/games/golden-wheel")
    csrf = await _csrf_from(wheel_page.text)

    resp = await client.post("/games/golden-wheel/spin", data={"bet": "50", "multiplier": "7", "csrf_token": csrf})
    assert resp.status_code == 400
    assert "Invalid multiplier" in resp.json()["error"]


async def test_wheel_spin_without_csrf_token_is_rejected(client):
    await _register(client, username="e2e_wheel_nocsrf", email="e2e_wheel_nocsrf@example.com")

    resp = await client.post("/games/golden-wheel/spin", data={"bet": "50", "multiplier": "2"})
    assert resp.status_code == 403
