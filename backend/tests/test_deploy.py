"""The single-origin deployment shape.

Two things are worth pinning down, because both fail silently rather than
loudly:

* the API lives under /api, so a page route and an endpoint can share a name;
* a deep link served by this process reaches the app rather than a 404.

The second set skips when there is no build on disk, which is the normal state
during development — `frontend/dist` is gitignored and Vite serves the app on
its own port.
"""

import re

import pytest

from app.config import API_PREFIX, SERVE_FRONTEND

HTML = {"Accept": "text/html,application/xhtml+xml"}

needs_build = pytest.mark.skipif(
    not SERVE_FRONTEND, reason="no frontend/dist — run `npm run build` in frontend/"
)


def test_the_api_lives_under_a_prefix(client):
    """Served from one origin, `/problems` is a page. It must not be an endpoint
    too, or the browser gets JSON where it asked for the site."""
    assert API_PREFIX == "/api"
    assert client.get(f"{API_PREFIX}/problems", params={"limit": 1}).status_code == 200


def test_the_oauth_callback_is_registered_under_the_prefix():
    """This string is copied into a provider's dashboard and has to match byte
    for byte, so a prefix change that missed it would break sign-in only in
    production."""
    from app.services.auth_service import redirect_uri

    assert redirect_uri("github").endswith("/api/auth/github/callback")


def test_health_stays_at_the_root(client):
    """It is the platform's probe, not part of the app's API, and no page claims
    the path."""
    assert client.get("/health").json()["status"] == "ok"


@needs_build
@pytest.mark.parametrize("path", ["/", "/problems", "/problems/two-sum", "/solve/two-sum", "/signin"])
def test_a_deep_link_reaches_the_app(client, path):
    r = client.get(path, headers=HTML)
    assert r.status_code == 200
    assert '<div id="root"' in r.text


@needs_build
def test_a_hashed_asset_is_served_as_itself(client):
    asset = re.search(r'/assets/[\w.\-]+\.js', client.get("/", headers=HTML).text).group(0)
    r = client.get(asset)
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]


@needs_build
def test_a_wrong_api_path_still_404s_as_json(client):
    """The index.html fallback is for browsers navigating. A fetch that asked
    for JSON and got a page would be a much harder bug to read."""
    r = client.get(f"{API_PREFIX}/problems/definitely-not-a-real-endpoint-xyz")
    assert r.status_code == 404
    assert '<div id="root"' not in r.text
