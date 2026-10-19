# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Shared pytest fixtures for the Personal Task Tracker."""

import pytest

from app import create_app
from app.db import init_db


@pytest.fixture
def app(tmp_path):
    """Create an app that uses its own temporary, freshly initialized database."""
    app = create_app({
        "TESTING": True,
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
