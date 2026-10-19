# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""User registration, login, logout, and session handling."""

import functools
import re
import sqlite3

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 8
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")
# A basic check: something@something.something with no spaces.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    """Redirect visitors who are not logged in to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    """Load the current user from the session into g.user for this request."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    # The user may have been deleted since logging in. Treat them as logged out.
    if g.user is None:
        session.clear()


def validate_registration(username, email, password, confirm_password):
    """Return a list of error messages for the submitted registration form."""
    errors = []

    if not username:
        errors.append("Username is required.")
    elif not USERNAME_PATTERN.match(username):
        errors.append("Username must be 3-30 characters using only letters, "
                      "numbers, and underscores.")

    if not email:
        errors.append("Email is required.")
    elif not EMAIL_PATTERN.match(email):
        errors.append("Please enter a valid email address.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    elif password != confirm_password:
        errors.append("Passwords do not match.")

    return errors


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Show the registration form and create new user accounts."""
    if g.user is not None:
        return redirect(url_for("main.dashboard"))

    username = ""
    email = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = validate_registration(username, email, password, confirm_password)

        if not errors:
            try:
                db = get_db()
                if db.execute("SELECT id FROM users WHERE username = ?",
                              (username,)).fetchone():
                    errors.append("That username is already taken.")
                if db.execute("SELECT id FROM users WHERE email = ?",
                              (email,)).fetchone():
                    errors.append("An account with that email already exists.")

                if not errors:
                    db.execute(
                        "INSERT INTO users (username, email, password_hash)"
                        " VALUES (?, ?, ?)",
                        (username, email, generate_password_hash(password)),
                    )
                    db.commit()
            except sqlite3.IntegrityError:
                # Another request registered the same name or email first.
                errors.append("That username or email is already registered.")
            except sqlite3.Error:
                current_app.logger.exception("Database error during registration")
                errors.append("Registration is unavailable right now. "
                              "Please try again later.")

        if not errors:
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

        for error in errors:
            flash(error, "danger")

    return render_template("auth/register.html", username=username, email=email)


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Show the login form and sign users in."""
    if g.user is not None:
        return redirect(url_for("main.dashboard"))

    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = get_db().execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        except sqlite3.Error:
            current_app.logger.exception("Database error during login")
            flash("Login is unavailable right now. Please try again later.", "danger")
            return render_template("auth/login.html", username=username)

        # Use the same message for unknown users and wrong passwords so the
        # form does not reveal which usernames exist.
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
        else:
            # Start a fresh session so no earlier session data carries over.
            session.clear()
            session["user_id"] = user["id"]
            flash("You are now logged in.", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", username=username)


@bp.route("/logout", methods=("POST",))
def logout():
    """Log the current user out and return to the homepage."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
