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


async def test_homepage_is_public_and_shows_catalog(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.url.path == "/"
    assert "Log In" in resp.text
    assert "Sign Up" in resp.text
    assert "Golden Reels" in resp.text  # seeded catalog game


async def test_authenticated_homepage_shows_balance(client):
    await _register(client, username="lobby_user", email="lobby_user@example.com")
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "1000 ₴" in resp.text


async def test_login_redirects_to_next_after_success(client):
    await _register(client, username="next_user", email="next_user@example.com", password="SuperSecret123")
    logout_page = await client.get("/")
    csrf = await _csrf_from(logout_page.text)
    await client.post("/auth/logout", data={"csrf_token": csrf})

    login_page = await client.get("/login?next=/games/slots")
    csrf2 = await _csrf_from(login_page.text)
    resp = await client.post(
        "/auth/login",
        data={"identifier": "next_user", "password": "SuperSecret123", "csrf_token": csrf2, "next": "/games/slots"},
    )
    assert resp.status_code == 200
    assert resp.url.path == "/games/slots"


async def test_login_ignores_unsafe_next(client):
    await _register(client, username="unsafe_next_user", email="unsafe_next_user@example.com")
    logout_page = await client.get("/")
    csrf = await _csrf_from(logout_page.text)
    await client.post("/auth/logout", data={"csrf_token": csrf})

    login_page = await client.get("/login?next=https://evil.example.com")
    csrf2 = await _csrf_from(login_page.text)
    # Crafted directly (bypassing whatever the hidden field rendered) to prove
    # the POST handler re-validates `next` itself rather than trusting the form.
    resp = await client.post(
        "/auth/login",
        data={
            "identifier": "unsafe_next_user",
            "password": "SuperSecret123",
            "csrf_token": csrf2,
            "next": "https://evil.example.com",
        },
    )
    assert resp.status_code == 200
    assert resp.url.path == "/"


async def test_slots_direct_access_redirects_with_next(client):
    resp = await client.get("/games/slots")
    assert resp.status_code == 200
    assert resp.url.path == "/login"
    assert "next=" in str(resp.url)


async def test_favorite_toggle_requires_auth(client):
    # A browser that merely visited the site (and thus has a CSRF cookie)
    # but never logged in should get 401, not a CSRF 403.
    await client.get("/")
    csrf_token = client.cookies.get("csrf_token")
    resp = await client.post("/games/slots/favorite", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 401


async def test_favorite_toggle_works_for_authenticated_user(client):
    home = await _register(client, username="fav_user", email="fav_user@example.com")
    csrf_token = client.cookies.get("csrf_token")

    resp = await client.post("/games/slots/favorite", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 200
    assert resp.json() == {"favorited": True}

    resp2 = await client.post("/games/slots/favorite", headers={"X-CSRF-Token": csrf_token})
    assert resp2.status_code == 200
    assert resp2.json() == {"favorited": False}


async def test_favorite_toggle_unknown_game_404s(client):
    home = await _register(client, username="fav_404_user", email="fav_404_user@example.com")
    csrf_token = client.cookies.get("csrf_token")

    resp = await client.post("/games/does-not-exist/favorite", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 404
