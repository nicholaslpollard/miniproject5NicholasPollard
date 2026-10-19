# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Tests for registration, login, logout, sessions, and CSRF protection."""

import logging
import re

import pytest
from werkzeug.security import check_password_hash

from app import create_app
from app.db import get_db

from conftest import get_csrf_token
from test_app import PUBLIC_PAGES, nav_links


def get_user(app, username="alice"):
    """Fetch a user row from the test database, or None."""
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def count_users(app):
    with app.app_context():
        return get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------- Registration ----------

def test_register_page_loads(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"<title>Register - Personal Task Tracker</title>" in response.data
    assert b'name="confirm_password"' in response.data


def test_successful_registration_creates_user(client, auth, app):
    response = auth.register()
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"

    user = get_user(app)
    assert user is not None
    assert user["email"] == "alice@example.com"


def test_registration_success_message_shown_on_login_page(client, auth):
    auth.register()
    response = client.get("/login")
    assert b"Registration successful. Please log in." in response.data


def test_password_is_stored_as_hash(auth, app):
    auth.register(password="password123")
    stored = get_user(app)["password_hash"]
    assert stored != "password123"
    assert "password123" not in stored
    assert stored.startswith(("scrypt:", "pbkdf2:"))
    assert check_password_hash(stored, "password123")


def test_registration_normalizes_input(auth, app):
    auth.register(username="  alice  ", email="  Alice@Example.COM ")
    user = get_user(app)
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"


@pytest.mark.parametrize("fields, message", [
    ({"username": ""}, b"Username is required."),
    ({"username": "a b!"}, b"Username must be 3-30 characters"),
    ({"username": "ab"}, b"Username must be 3-30 characters"),
    ({"email": ""}, b"Email is required."),
    ({"email": "not-an-email"}, b"Please enter a valid email address."),
    ({"email": "alice@example"}, b"Please enter a valid email address."),
    ({"password": "", "confirm_password": ""}, b"Password is required."),
    ({"password": "short", "confirm_password": "short"},
     b"Password must be at least 8 characters."),
    ({"confirm_password": "different123"}, b"Passwords do not match."),
])
def test_invalid_registration_is_rejected(auth, app, fields, message):
    response = auth.register(**fields)
    assert response.status_code == 200
    assert message in response.data
    assert count_users(app) == 0


def test_registration_form_keeps_entered_values_but_not_password(auth):
    response = auth.register(password="password123", confirm_password="mismatch999")
    html = response.get_data(as_text=True)
    assert 'value="alice"' in html
    assert 'value="alice@example.com"' in html
    assert "password123" not in html


def test_duplicate_username_is_rejected(auth, app):
    auth.register()
    response = auth.register(email="other@example.com")
    assert b"That username is already taken." in response.data
    assert count_users(app) == 1


def test_duplicate_email_is_rejected_case_insensitively(auth, app):
    auth.register()
    response = auth.register(username="bob", email="ALICE@example.com")
    assert b"An account with that email already exists." in response.data
    assert count_users(app) == 1


def test_plaintext_password_is_never_logged(auth, caplog):
    caplog.set_level(logging.DEBUG)
    auth.register(password="SuperSecret999")
    auth.login(password="SuperSecret999")
    auth.login(password="WrongSecret999")
    assert "SuperSecret999" not in caplog.text
    assert "WrongSecret999" not in caplog.text


# ---------- Login ----------

def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"<title>Login - Personal Task Tracker</title>" in response.data


def test_correct_credentials_log_in(client, auth, app):
    auth.register()
    response = auth.login()
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"

    with client.session_transaction() as sess:
        assert sess["user_id"] == get_user(app)["id"]


def test_login_session_stores_only_user_id(client, auth):
    auth.register(password="password123")
    auth.login(password="password123")
    with client.session_transaction() as sess:
        # Flask's own flash storage and the CSRF token are not user data.
        user_keys = set(sess.keys()) - {"_flashes", "_csrf_token"}
        assert user_keys == {"user_id"}
        assert "password123" not in str(dict(sess))


def test_login_clears_previous_session_data(client, auth):
    auth.register()
    with client.session_transaction() as sess:
        sess["leftover"] = "old value"
    auth.login()
    with client.session_transaction() as sess:
        assert "leftover" not in sess


@pytest.mark.parametrize("username, password", [
    ("alice", "wrongpassword"),
    ("nobody", "password123"),
    ("", ""),
])
def test_bad_credentials_are_rejected_generically(client, auth, username, password):
    auth.register()
    response = auth.login(username, password)
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# ---------- Logout ----------

def test_logout_clears_session(client, auth):
    auth.register()
    auth.login()
    response = auth.logout()
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as sess:
        assert "user_id" not in sess
    assert client.get("/dashboard").status_code == 302


def test_logout_requires_post(client, auth):
    auth.register()
    auth.login()
    assert client.get("/logout").status_code == 405
    with client.session_transaction() as sess:
        assert "user_id" in sess


# ---------- Protected pages and current user ----------

def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert b"Please log in to access that page." in client.get("/login").data


def test_dashboard_shows_username(client, auth):
    auth.register()
    auth.login()
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Welcome, alice!" in response.data
    assert b"Task management will be added in the next development stage." in response.data


def test_logged_in_user_is_redirected_from_login_and_register(client, auth):
    auth.register()
    auth.login()
    assert client.get("/login").headers["Location"] == "/dashboard"
    assert client.get("/register").headers["Location"] == "/dashboard"


def test_invalid_user_id_in_session_is_logged_out(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 9999
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log Out" not in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_deleted_user_is_logged_out(client, auth, app):
    auth.register()
    auth.login()
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM users WHERE username = ?", ("alice",))
        db.commit()
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


# ---------- Navigation ----------

def test_logged_out_navigation(client):
    html = client.get("/").get_data(as_text=True)
    assert nav_links(html) == [page[0] for page in PUBLIC_PAGES]
    assert nav_links(html, "accountNav") == ["/register", "/login"]
    assert "Log Out" not in html


def test_logged_in_navigation(client, auth):
    auth.register()
    auth.login()
    html = client.get("/").get_data(as_text=True)
    assert nav_links(html) == [page[0] for page in PUBLIC_PAGES]
    assert nav_links(html, "accountNav") == ["/dashboard"]
    assert "Signed in as alice" in html
    assert re.search(r'<form action="/logout" method="post"', html)
    assert "/register" not in nav_links(html, "accountNav")


@pytest.mark.parametrize("path", ["/register", "/login"])
def test_auth_pages_have_active_indicator(client, path):
    html = client.get(path).get_data(as_text=True)
    active = re.findall(r'<a class="nav-link active" aria-current="page"\s+href="([^"]+)"', html)
    assert active == [path]


def test_dashboard_has_active_indicator(client, auth):
    auth.register()
    auth.login()
    html = client.get("/dashboard").get_data(as_text=True)
    active = re.findall(r'<a class="nav-link active" aria-current="page"\s+href="([^"]+)"', html)
    assert active == ["/dashboard"]


@pytest.mark.parametrize("path", [page[0] for page in PUBLIC_PAGES])
def test_public_pages_work_when_logged_in(client, auth, path):
    auth.register()
    auth.login()
    assert client.get(path).status_code == 200


# ---------- CSRF protection ----------

@pytest.mark.parametrize("path", ["/register", "/login"])
def test_forms_include_session_csrf_token(client, path):
    html = client.get(path).get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert token == get_csrf_token(client)


def test_logout_form_includes_csrf_token(client, auth):
    auth.register()
    auth.login()
    html = client.get("/").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert token == get_csrf_token(client)


@pytest.mark.parametrize("token", [None, "", "wrong-token"])
def test_register_rejects_bad_csrf_token(client, app, token):
    get_csrf_token(client)
    data = {"username": "alice", "email": "alice@example.com",
            "password": "password123", "confirm_password": "password123"}
    if token is not None:
        data["csrf_token"] = token
    response = client.post("/register", data=data)
    assert response.status_code == 400
    assert b"Bad Request" in response.data
    assert count_users(app) == 0


def test_login_rejects_bad_csrf_token(client, auth):
    auth.register()
    response = client.post("/login", data={
        "username": "alice", "password": "password123", "csrf_token": "wrong-token",
    })
    assert response.status_code == 400
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_post_without_any_session_token_is_rejected(app):
    """A forged request from a fresh browser has no session token at all."""
    response = app.test_client().post("/login", data={
        "username": "alice", "password": "password123", "csrf_token": "guess",
    })
    assert response.status_code == 400


def test_logout_rejects_bad_csrf_token(client, auth):
    auth.register()
    auth.login()
    response = client.post("/logout", data={"csrf_token": "wrong-token"})
    assert response.status_code == 400
    with client.session_transaction() as sess:
        assert "user_id" in sess


# ---------- Error handling ----------

@pytest.fixture
def broken_db_app(tmp_path):
    """An app whose database file exists but has no tables."""
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "empty.sqlite"),
    })


def test_register_database_error_is_handled(broken_db_app):
    client = broken_db_app.test_client()
    response = client.post("/register", data={
        "username": "alice", "email": "alice@example.com",
        "password": "password123", "confirm_password": "password123",
        "csrf_token": get_csrf_token(client),
    })
    assert response.status_code == 200
    assert b"Registration is unavailable right now." in response.data
    assert b"no such table" not in response.data


def test_login_database_error_is_handled(broken_db_app):
    client = broken_db_app.test_client()
    response = client.post("/login", data={
        "username": "alice", "password": "password123",
        "csrf_token": get_csrf_token(client),
    })
    assert response.status_code == 200
    assert b"Login is unavailable right now." in response.data
    assert b"no such table" not in response.data


def test_unexpected_error_shows_friendly_page(broken_db_app):
    broken_db_app.config["PROPAGATE_EXCEPTIONS"] = False
    client = broken_db_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.get("/")
    assert response.status_code == 500
    assert b"Something Went Wrong" in response.data
    assert b"no such table" not in response.data
    assert b"Traceback" not in response.data


# ---------- Configuration ----------

def test_secret_key_comes_from_environment(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "from-environment")
    assert create_app().config["SECRET_KEY"] == "from-environment"


def test_dev_secret_key_logs_warning(monkeypatch, caplog):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with caplog.at_level(logging.WARNING):
        create_app()
    assert "insecure development SECRET_KEY" in caplog.text
