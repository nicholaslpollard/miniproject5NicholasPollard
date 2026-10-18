# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Smoke tests for the Personal Task Tracker."""

import pytest

from app import create_app


@pytest.fixture
def client():
    """Create a test client for the application."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_app_is_in_testing_mode():
    """The factory should apply the test configuration."""
    assert create_app({"TESTING": True}).testing


def test_homepage_loads(client):
    """The homepage should respond successfully and render the base template."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Personal Task Tracker" in response.data
    assert b"bootstrap" in response.data
