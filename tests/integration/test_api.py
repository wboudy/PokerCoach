"""Integration tests for the API."""

import pytest
from fastapi.testclient import TestClient

from pokercoach.web.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert response.json()["version"] == "0.1.0"

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestCoachEndpoints:
    """Test coach API endpoints."""

    def test_ask_coach(self, client):
        response = client.post(
            "/api/coach/ask",
            json={"question": "What is a c-bet?"},
        )
        assert response.status_code == 200
        assert "answer" in response.json()

    def test_query_gto(self, client):
        response = client.post(
            "/api/coach/gto",
            json={
                "hand": "AsKs",
                "position": "BTN",
                "pot_size": 10,
                "to_call": 0,
            },
        )
        assert response.status_code == 200
        assert "actions" in response.json()


class TestAnalysisEndpoints:
    """Test analysis API endpoints."""

    def test_get_sessions_empty(self, client):
        response = client.get("/api/analysis/sessions")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_session_not_found(self, client):
        response = client.get("/api/analysis/sessions/nonexistent")
        assert response.status_code == 404

    def test_get_leaks_empty(self, client):
        response = client.get("/api/analysis/leaks")
        assert response.status_code == 200
        assert response.json() == []


class TestOpponentsEndpoints:
    """Test opponents API endpoints."""

    def test_list_players_empty(self, client):
        response = client.get("/api/opponents/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_player_not_found(self, client):
        response = client.get("/api/opponents/unknown_player")
        assert response.status_code == 404

    def test_search_players_empty(self, client):
        response = client.get("/api/opponents/search/test")
        assert response.status_code == 200
        assert response.json() == []
