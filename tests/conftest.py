# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Shared pytest fixtures for the Personal Task Tracker."""

import secrets

import pytest

from app import create_app
from app.csrf import CSRF_SESSION_KEY
from app.db import init_db


@pytest.fixture
def app(tmp_path):
    """Create an app that uses its own temporary, freshly initialized database."""
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "test.sqlite"),
    })
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    """Create a test client for the application."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(app):
    """Create a runner for the application's CLI commands."""
    return app.test_cli_runner()


def get_csrf_token(client):
    """Return the client's session CSRF token, creating one if needed."""
    with client.session_transaction() as sess:
        return sess.setdefault(CSRF_SESSION_KEY, secrets.token_hex(32))


class AuthActions:
    """Helper methods for registering, logging in, and logging out in tests."""

    def __init__(self, client):
        self._client = client

    def register(self, username="alice", email="alice@example.com",
                 password="password123", confirm_password=None):
        if confirm_password is None:
            confirm_password = password
        return self._client.post("/register", data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": confirm_password,
            "csrf_token": get_csrf_token(self._client),
        })

    def login(self, username="alice", password="password123"):
        return self._client.post("/login", data={
            "username": username,
            "password": password,
            "csrf_token": get_csrf_token(self._client),
        })

    def logout(self):
        return self._client.post("/logout", data={
            "csrf_token": get_csrf_token(self._client),
        })


@pytest.fixture
def auth(client):
    """Provide authentication helper actions bound to the test client."""
    return AuthActions(client)
