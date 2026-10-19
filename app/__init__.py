# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Application factory for the Personal Task Tracker."""

import os

from flask import Flask

# Fallback key for local development only. It is publicly known, so anyone
# could forge session cookies signed with it. Always set the SECRET_KEY
# environment variable to a long random value outside of development.
DEV_SECRET_KEY = "dev"


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", DEV_SECRET_KEY),
        DATABASE=os.path.join(app.instance_path, "tasktracker.sqlite"),
        # Keep the session cookie away from JavaScript and cross-site requests.
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    # Allow tests to pass in their own configuration.
    if test_config is not None:
        app.config.from_mapping(test_config)

    if app.config["SECRET_KEY"] == DEV_SECRET_KEY and not app.testing:
        app.logger.warning(
            "Using the insecure development SECRET_KEY. "
            "Set the SECRET_KEY environment variable before deploying."
        )

    # The instance folder will hold local files such as the SQLite database.
    os.makedirs(app.instance_path, exist_ok=True)

    # Register database connection handling and the init-db command.
    from . import db
    db.init_app(app)

    # Require a valid CSRF token on every POST form.
    from . import csrf
    csrf.init_app(app)

    # Register blueprints.
    from . import auth, main
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)

    return app
