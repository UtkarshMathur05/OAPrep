import pytest


def test_list_shape(client):
    body = client.get("/problems", params={"limit": 3}).json()
    assert set(body) == {"total", "limit", "offset", "problems"}
    assert len(body["problems"]) <= 3
    # total is the filter count, not the page size
    assert body["total"] >= len(body["problems"])


def test_list_has_no_reconstruction_fields(client):
    """A corpus row must not pretend to carry Gemini's output."""
    rows = client.get("/problems", params={"limit": 1}).json()["problems"]
    if rows:
        assert not {"constraints", "examples", "confidence"} & set(rows[0])


def test_pagination_differs(client):
    a = client.get("/problems", params={"limit": 2, "offset": 0}).json()["problems"]
    b = client.get("/problems", params={"limit": 2, "offset": 2}).json()["problems"]
    if len(a) == 2 and len(b) >= 1:
        assert {r["slug"] for r in a}.isdisjoint({r["slug"] for r in b})


def test_difficulty_filter(client):
    rows = client.get("/problems", params={"difficulty": "hard", "limit": 5}).json()["problems"]
    assert all(r["difficulty"] == "hard" for r in rows)


def test_company_filter_uses_gin(client):
    body = client.get("/problems", params={"company": "google", "limit": 5}).json()
    for row in body["problems"]:
        # companies is sliced to 5 for display, so the filter term may not be
        # in the visible slice — but the count must be real.
        assert row["company_count"] >= 1


def test_search_filter(client):
    rows = client.get("/problems", params={"search": "path", "limit": 5}).json()["problems"]
    assert all("path" in r["title"].lower() for r in rows)


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_limit_out_of_range_is_422(client, limit):
    assert client.get("/problems", params={"limit": limit}).status_code == 422


def test_detail_by_slug_and_uuid(client, any_slug):
    by_slug = client.get(f"/problems/{any_slug}").json()
    by_uuid = client.get(f"/problems/{by_slug['id']}").json()
    assert by_slug["id"] == by_uuid["id"]
    assert {"description", "has_embedding", "test_case_count"} <= set(by_slug)


def test_detail_404_not_500(client):
    # A malformed id must not reach Postgres as a broken uuid cast.
    for ident in ("does-not-exist", "00000000-0000-0000-0000-000000000000", "not-a-uuid"):
        assert client.get(f"/problems/{ident}").status_code == 404
