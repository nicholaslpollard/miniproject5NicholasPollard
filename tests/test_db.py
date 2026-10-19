# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Tests for the SQLite database schema and connection management."""

import os
import sqlite3

import pytest

from app import create_app
from app.db import get_db, init_db


def add_user(db, username="alice", email="alice@example.com", password_hash="hashed-pw"):
    """Insert a user and return the new user's id."""
    cursor = db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash),
    )
    db.commit()
    return cursor.lastrowid


def add_task(db, user_id, title="Sample task", description=None):
    """Insert a task for the given user and return the new task's id."""
    cursor = db.execute(
        "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
        (user_id, title, description),
    )
    db.commit()
    return cursor.lastrowid


def column_names(db, table):
    """Return the set of column names for a table."""
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}


# ---------- Initialization ----------

def test_init_db_creates_both_tables(app):
    with app.app_context():
        rows = get_db().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        tables = {row["name"] for row in rows}
    assert {"users", "tasks"} <= tables


def test_users_table_columns(app):
    with app.app_context():
        columns = column_names(get_db(), "users")
    assert columns == {"id", "username", "email", "password_hash", "created_at"}


def test_tasks_table_columns(app):
    with app.app_context():
        columns = column_names(get_db(), "tasks")
    assert columns == {"id", "user_id", "title", "description", "completed", "created_at"}


def test_tasks_foreign_key_is_declared(app):
    with app.app_context():
        fk = get_db().execute("PRAGMA foreign_key_list(tasks)").fetchone()
    assert fk["table"] == "users"
    assert fk["from"] == "user_id"
    assert fk["to"] == "id"
    assert fk["on_delete"] == "CASCADE"


def test_init_db_does_not_erase_existing_data(app):
    """Running initialization again must keep existing records."""
    with app.app_context():
        db = get_db()
        add_user(db)
        init_db()
        count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 1


def test_init_db_command(runner, monkeypatch):
    """The init-db CLI command should call init_db and report success."""
    called = []
    monkeypatch.setattr("app.db.init_db", lambda: called.append(True))
    result = runner.invoke(args=["init-db"])
    assert "Initialized the database." in result.output
    assert called


def test_init_db_command_creates_real_database(tmp_path):
    """The init-db command should create the tables in a new database file."""
    db_path = tmp_path / "cli.sqlite"
    app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    assert db_path.exists()
    with app.app_context():
        assert column_names(get_db(), "users")


def test_app_startup_does_not_create_database(tmp_path):
    """Creating the app must not create or modify a database automatically."""
    db_path = tmp_path / "untouched.sqlite"
    app = create_app({"TESTING": True, "DATABASE": str(db_path)})
    app.test_client().get("/")
    assert not db_path.exists()


def test_default_database_is_in_instance_folder():
    app = create_app({"TESTING": True})
    assert app.config["DATABASE"] == os.path.join(app.instance_path, "tasktracker.sqlite")


# ---------- Users ----------

def test_insert_and_retrieve_user(app):
    with app.app_context():
        db = get_db()
        user_id = add_user(db)
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"
    assert user["password_hash"] == "hashed-pw"
    assert user["created_at"] is not None


def test_username_must_be_unique(app):
    with app.app_context():
        db = get_db()
        add_user(db)
        with pytest.raises(sqlite3.IntegrityError, match="users.username"):
            add_user(db, email="other@example.com")


def test_email_must_be_unique(app):
    with app.app_context():
        db = get_db()
        add_user(db)
        with pytest.raises(sqlite3.IntegrityError, match="users.email"):
            add_user(db, username="bob")


def test_password_hash_is_required(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError, match="users.password_hash"):
            db.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                ("carol", "carol@example.com"),
            )


# ---------- Tasks ----------

def test_task_references_valid_user(app):
    with app.app_context():
        db = get_db()
        user_id = add_user(db)
        task_id = add_task(db, user_id, "Write report", "Due Friday")
        task = db.execute(
            "SELECT tasks.*, users.username FROM tasks"
            " JOIN users ON tasks.user_id = users.id WHERE tasks.id = ?",
            (task_id,),
        ).fetchone()
    assert task["title"] == "Write report"
    assert task["description"] == "Due Friday"
    assert task["completed"] == 0
    assert task["username"] == "alice"
    assert task["created_at"] is not None


def test_task_title_is_required(app):
    with app.app_context():
        db = get_db()
        user_id = add_user(db)
        with pytest.raises(sqlite3.IntegrityError, match="tasks.title"):
            db.execute("INSERT INTO tasks (user_id) VALUES (?)", (user_id,))


def test_foreign_key_rejects_invalid_user(app):
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            add_task(get_db(), user_id=9999)


def test_deleting_user_cascades_to_tasks(app):
    with app.app_context():
        db = get_db()
        alice = add_user(db)
        bob = add_user(db, "bob", "bob@example.com")
        add_task(db, alice, "Alice task 1")
        add_task(db, alice, "Alice task 2")
        add_task(db, bob, "Bob task")

        db.execute("DELETE FROM users WHERE id = ?", (alice,))
        db.commit()

        remaining = db.execute("SELECT user_id FROM tasks").fetchall()
    assert [row["user_id"] for row in remaining] == [bob]


# ---------- Connection management ----------

def test_get_db_returns_same_connection_in_context(app):
    with app.app_context():
        assert get_db() is get_db()


def test_connection_settings(app):
    with app.app_context():
        db = get_db()
        assert db.row_factory is sqlite3.Row
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_connection_closed_after_context(app):
    with app.app_context():
        db = get_db()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        db.execute("SELECT 1")


def test_new_context_gets_new_connection(app):
    with app.app_context():
        first = get_db()
    with app.app_context():
        second = get_db()
    assert first is not second
