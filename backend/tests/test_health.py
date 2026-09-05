def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    # Flags the demo depends on; ai_ready must not be fooled by a placeholder.
    assert set(body) >= {"status", "mock_ai", "ai_ready"}


def test_health_db_reports_corpus(client):
    body = client.get("/health/db").json()
    assert body["status"] == "ok"
    assert body["problems"] >= 0
    assert body["embedded"] <= body["problems"]
