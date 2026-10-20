from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.cache import TTLCache


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Tactical_XI"
    assert data["status"] == "running"


def test_matches_endpoint():
    response = client.get("/matches")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_cache_stores_and_returns_value():
    cache = TTLCache(ttl_seconds=300)

    cache.set("test-match", {"goals": 2})

    assert cache.get("test-match") == {"goals": 2}


def test_cache_returns_none_for_missing_key():
    cache = TTLCache(ttl_seconds=300)

    assert cache.get("missing-match") is None


def test_cache_delete():
    cache = TTLCache(ttl_seconds=300)

    cache.set("test-match", {"goals": 2})
    cache.delete("test-match")

    assert cache.get("test-match") is None


def test_cache_clear():
    cache = TTLCache(ttl_seconds=300)

    cache.set("match-1", {"value": 1})
    cache.set("match-2", {"value": 2})
    cache.clear()

    assert cache.get("match-1") is None
    assert cache.get("match-2") is None