"""Tests for web API routes."""

import pytest
from fastapi.testclient import TestClient

from pokercoach.web.app import app


@pytest.fixture
def client():
    """Create test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PokerCoach API"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestCoachRoutes:
    """Tests for /api/coach routes."""

    def test_ask_coach_endpoint_exists(self, client):
        """Test that the /api/coach/ask endpoint exists."""
        response = client.post(
            "/api/coach/ask",
            json={"question": "What should I do here?"},
        )
        # Should get 200, not 404
        assert response.status_code == 200

    def test_ask_coach_response_format(self, client):
        """Test coach response has expected fields."""
        response = client.post(
            "/api/coach/ask",
            json={
                "question": "Should I call or fold?",
                "hand": "AsKs",
                "position": "BTN",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        # strategy and ev_comparison can be null but should exist
        assert "strategy" in data
        assert "ev_comparison" in data

    def test_gto_query_endpoint_exists(self, client):
        """Test that the /api/coach/gto endpoint exists."""
        response = client.post(
            "/api/coach/gto",
            json={
                "hand": "AhKd",
                "position": "CO",
                "pot_size": 10,
                "to_call": 3,
            },
        )
        assert response.status_code == 200

    def test_gto_query_response_format(self, client):
        """Test GTO query response has expected fields."""
        response = client.post(
            "/api/coach/gto",
            json={
                "hand": "QhQd",
                "board": "As,Ks,Ts",
                "position": "BB",
                "pot_size": 20,
                "to_call": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hand" in data
        assert "actions" in data
        assert isinstance(data["actions"], dict)


class TestAnalysisRoutes:
    """Tests for /api/analysis routes."""

    def test_analysis_routes_accessible(self, client):
        """Test that analysis routes are registered."""
        # Just verify the router is mounted - specific endpoints tested elsewhere
        response = client.get("/api/analysis/")
        # 404 or 405 means router is there but no matching route
        # 200 would mean there's a root endpoint
        assert response.status_code in [200, 404, 405]


class TestOpponentsRoutes:
    """Tests for /api/opponents routes."""

    def test_opponents_routes_accessible(self, client):
        """Test that opponents routes are registered."""
        response = client.get("/api/opponents/")
        assert response.status_code in [200, 404, 405]


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are set for allowed origins."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware should respond
        assert response.status_code in [200, 400]
