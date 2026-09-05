"""Memory extraction and persistence.

The real-AI path is exercised with a stubbed Gemini call, so the wiring is
verified without a key and without spending quota.
"""

import pytest

from app.schemas.memory import Genome


def test_mock_mode_returns_shaped_genome(client):
    body = client.post("/memory", json={"transcript": "grid, right or down, min cost"}).json()
    assert set(body["memory"]) == set(Genome.model_fields)


def test_memory_is_persisted_with_real_uuid(client):
    from uuid import UUID

    body = client.post("/memory", json={"transcript": "a remembered grid problem"}).json()
    UUID(body["memory_id"])  # raises if it is still "mock-memory-1"


def test_round_trip_keeps_all_seven_fields(client):
    """data_structures and algorithm_hints had no columns once; they do now."""
    created = client.post("/memory", json={"transcript": "round trip check"}).json()
    fetched = client.get(f"/memory/{created['memory_id']}").json()
    assert set(fetched["memory"]) == set(Genome.model_fields)
    assert fetched["memory_id"] == created["memory_id"]


def test_empty_transcript_is_422(client):
    assert client.post("/memory", json={"transcript": "   "}).status_code == 422


def test_unknown_memory_is_404(client):
    for ident in ("00000000-0000-0000-0000-000000000000", "not-a-uuid"):
        assert client.get(f"/memory/{ident}").status_code == 404


def test_real_extraction_path(client, monkeypatch):
    """Wire /memory to ai.extraction with Gemini stubbed out.

    Proves the ProblemGenome -> Genome conversion and the config gate, which is
    everything that can break here that is not Gemini's own behaviour.
    """
    from ai.models.problem_genome import ProblemGenome
    from app.services import ai_service

    captured = {}

    def fake_extract(transcript: str) -> ProblemGenome:
        captured["transcript"] = transcript
        return ProblemGenome(
            concepts=["binary search"],
            operations=["halve the range"],
            objective="find the pivot",
            data_structures=["sorted array"],
            algorithm_hints=["two pointers"],
            uncertainties=["whether duplicates were allowed"],
        )

    import ai.extraction.genome as genome_module
    monkeypatch.setattr(genome_module, "extract_genome", fake_extract)
    # Force the live branch: mock off, key present.
    monkeypatch.setattr(ai_service, "USE_MOCK_AI", False)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "test-key")

    body = client.post("/memory", json={"transcript": "something about a rotated array"}).json()

    assert captured["transcript"] == "something about a rotated array"
    assert body["memory"]["concepts"] == ["binary search"]
    assert body["memory"]["uncertainties"] == ["whether duplicates were allowed"]
    # The uncertain detail must not have been promoted into constraints (§19).
    assert body["memory"]["constraints"] == []
    # And it was persisted, not just echoed.
    stored = client.get(f"/memory/{body['memory_id']}").json()
    assert stored["memory"]["algorithm_hints"] == ["two pointers"]


def test_missing_key_falls_back_to_mock(client, monkeypatch):
    """A teammate with USE_MOCK_AI=false but no key still gets a valid response."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service, "USE_MOCK_AI", False)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "")
    resp = client.post("/memory", json={"transcript": "no key configured"})
    assert resp.status_code == 200
    assert set(resp.json()["memory"]) == set(Genome.model_fields)
