# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Task creation, editing, completion, and deletion."""

import sqlite3

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template,
    request, url_for,
)

from .auth import login_required
from .db import get_db

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 1000


def get_user_task(task_id):
    """Return the task with this ID if it belongs to the logged-in user.

    Responds with 404 when the task does not exist or belongs to someone
    else, so other users' task IDs are never revealed.
    """
    task = get_db().execute(
        "SELECT id, title, description, completed, created_at FROM tasks"
        " WHERE id = ? AND user_id = ?",
        (task_id, g.user["id"]),
    ).fetchone()

    if task is None:
        abort(404)
    return task


def read_task_form():
    """Return the trimmed title and description submitted in the form."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    return title, description


def validate_task(title, description):
    """Return a list of error messages for the submitted task fields."""
    errors = []

    if not title:
        errors.append("Title is required.")
    elif len(title) > MAX_TITLE_LENGTH:
        errors.append(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.")

    return errors


def render_task_form(title, description, task=None):
    """Show the shared create/edit form with the given field values."""
    return render_template(
        "tasks/task_form.html",
        task=task,
        title=title,
        description=description,
        max_title=MAX_TITLE_LENGTH,
        max_description=MAX_DESCRIPTION_LENGTH,
    )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def create():
    """Show the new task form and save new tasks."""
    if request.method == "GET":
        return render_task_form("", "")

    title, description = read_task_form()
    errors = validate_task(title, description)

    if not errors:
        try:
            db = get_db()
            # The owner always comes from the session, never from the form.
            db.execute(
                "INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
                (g.user["id"], title, description or None),
            )
            db.commit()
        except sqlite3.Error:
            current_app.logger.exception("Database error while creating a task")
            errors.append("The task could not be saved right now. Please try again.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return render_task_form(title, description)

    flash("Task created.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/<int:task_id>/edit", methods=("GET", "POST"))
@login_required
def edit(task_id):
    """Show the edit form for a task and save changes to it."""
    task = get_user_task(task_id)

    if request.method == "GET":
        return render_task_form(task["title"], task["description"] or "", task)

    title, description = read_task_form()
    errors = validate_task(title, description)

    if not errors:
        try:
            db = get_db()
            db.execute(
                "UPDATE tasks SET title = ?, description = ?"
                " WHERE id = ? AND user_id = ?",
                (title, description or None, task_id, g.user["id"]),
            )
            db.commit()
        except sqlite3.Error:
            current_app.logger.exception("Database error while editing a task")
            errors.append("The task could not be updated right now. Please try again.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return render_task_form(title, description, task)

    flash("Task updated.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/<int:task_id>/toggle", methods=("POST",))
@login_required
def toggle(task_id):
    """Switch a task between complete and incomplete."""
    task = get_user_task(task_id)
    new_status = 0 if task["completed"] else 1

    try:
        db = get_db()
        db.execute(
            "UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?",
            (new_status, task_id, g.user["id"]),
        )
        db.commit()
    except sqlite3.Error:
        current_app.logger.exception("Database error while updating task status")
        flash("The task could not be updated right now. Please try again.", "danger")
    else:
        if new_status:
            flash(f'Marked "{task["title"]}" as complete.', "success")
        else:
            flash(f'Marked "{task["title"]}" as incomplete.', "info")

    return redirect(url_for("main.dashboard"))


@bp.route("/<int:task_id>/delete", methods=("POST",))
@login_required
def delete(task_id):
    """Delete a task after the user confirms in the modal."""
    task = get_user_task(task_id)

    try:
        db = get_db()
        db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, g.user["id"]),
        )
        db.commit()
    except sqlite3.Error:
        current_app.logger.exception("Database error while deleting a task")
        flash("The task could not be deleted right now. Please try again.", "danger")
    else:
        flash(f'Deleted "{task["title"]}".', "success")

    return redirect(url_for("main.dashboard"))
