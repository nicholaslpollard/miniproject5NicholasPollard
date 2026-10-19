# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Simple CSRF protection for POST forms.

Each session receives a random token. Every form includes the token in a
hidden field, and every POST request must send back the matching token.
A malicious site cannot read the token, so it cannot forge a valid form.
"""

import secrets

from flask import abort, request, session

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token():
    """Return the CSRF token for this session, creating one if needed."""
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_hex(32)
    return session[CSRF_SESSION_KEY]


def validate_csrf_token():
    """Reject any POST request whose CSRF token is missing or incorrect."""
    if request.method != "POST":
        return

    expected = session.get(CSRF_SESSION_KEY)
    submitted = request.form.get(CSRF_FORM_FIELD, "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400, description="Your form session has expired or is invalid. "
                               "Please go back, refresh the page, and try again.")


def init_app(app):
    """Register CSRF checking and make csrf_token() available in templates."""
    app.jinja_env.globals["csrf_token"] = generate_csrf_token
    app.before_request(validate_csrf_token)
