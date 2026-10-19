# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""SQLite database connection management for the Personal Task Tracker."""

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """Return the database connection for the current application context.

    The connection is created on first use and reused until the context ends.
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        # Allow columns to be accessed by name, e.g. row["username"].
        g.db.row_factory = sqlite3.Row
        # SQLite only enforces foreign keys when this is enabled per connection.
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Close the database connection if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the database tables defined in schema.sql."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database tables if they do not already exist."""
    init_db()
    click.echo("Initialized the database.")


def init_app(app):
    """Register database functions with the Flask application."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
