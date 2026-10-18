# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Application factory for the Personal Task Tracker."""

import os

from flask import Flask


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Default settings. SECRET_KEY should be overridden by an environment
    # variable in any real deployment.
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
    )

    # Allow tests to pass in their own configuration.
    if test_config is not None:
        app.config.from_mapping(test_config)

    # The instance folder will hold local files such as the SQLite database.
    os.makedirs(app.instance_path, exist_ok=True)

    # Register blueprints.
    from . import main
    app.register_blueprint(main.bp)

    return app
