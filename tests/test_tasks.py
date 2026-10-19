# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Tests for task management, ownership rules, and the delete modal."""

import re

import pytest

from app.db import get_db

from conftest import get_csrf_token
from test_app import PUBLIC_PAGES


# ---------- Helpers ----------

def create_task(client, title="Buy groceries", description="Milk and eggs"):
    return client.post("/tasks/new", data={
        "title": title,
        "description": description,
        "csrf_token": get_csrf_token(client),
    })


def post_with_token(client, url, data=None):
    data = dict(data or {})
    data["csrf_token"] = get_csrf_token(client)
    return client.post(url, data=data)


def fetch_tasks(app):
    """Return every task row in the test database, oldest first."""
    with app.app_context():
        return get_db().execute("SELECT * FROM tasks ORDER BY id").fetchall()


def fetch_task(app, task_id):
    with app.app_context():
        return get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def user_id(app, username):
    with app.app_context():
        return get_db().execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()["id"]


def dashboard_html(client):
    return client.get("/dashboard").get_data(as_text=True)


def stat(html, name):
    return int(re.search(rf'id="stat{name}">(\d+)<', html).group(1))


def task_titles(html):
    return re.findall(r'<h2 class="h5 card-title mb-1 task-title">(.*?)</h2>', html)


@pytest.fixture
def logged_in(auth):
    """Register and log in as alice."""
    auth.register()
    auth.login()
    return auth


@pytest.fixture
def other_users_task(client, auth, app):
    """Create a task owned by bob, then log in as alice. Returns bob's task id."""
    auth.register("bob", "bob@example.com")
    auth.login("bob")
    create_task(client, "Bob's private task", "Bob only")
    auth.logout()
    auth.register()
    auth.login()
    return fetch_tasks(app)[0]["id"]


# ---------- Authentication required ----------

@pytest.mark.parametrize("path", ["/dashboard", "/tasks/new", "/tasks/1/edit"])
def test_get_task_routes_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


@pytest.mark.parametrize("path", [
    "/tasks/new", "/tasks/1/edit", "/tasks/1/toggle", "/tasks/1/delete",
])
def test_post_task_routes_require_login(client, app, path):
    response = post_with_token(client, path, {"title": "Sneaky"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert fetch_tasks(app) == []


# ---------- Creating tasks ----------

def test_new_task_page_loads(client, logged_in):
    response = client.get("/tasks/new")
    assert response.status_code == 200
    assert b"<title>New Task - Personal Task Tracker</title>" in response.data
    assert b'name="title"' in response.data
    assert b'name="description"' in response.data
    assert b'name="csrf_token"' in response.data


def test_create_task_succeeds(client, logged_in, app):
    response = create_task(client, "  Buy groceries  ", "  Milk and eggs  ")
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"

    tasks = fetch_tasks(app)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Buy groceries"
    assert tasks[0]["description"] == "Milk and eggs"
    assert tasks[0]["completed"] == 0
    assert tasks[0]["created_at"]
    assert b"Task created." in client.get("/dashboard").data


def test_task_belongs_to_logged_in_user(client, logged_in, app):
    create_task(client)
    assert fetch_tasks(app)[0]["user_id"] == user_id(app, "alice")


def test_submitted_user_id_is_ignored(client, auth, app):
    auth.register("bob", "bob@example.com")
    auth.register()
    auth.login()
    post_with_token(client, "/tasks/new", {
        "title": "Forged owner", "user_id": str(user_id(app, "bob")),
    })
    assert fetch_tasks(app)[0]["user_id"] == user_id(app, "alice")


def test_empty_description_is_stored_as_null(client, logged_in, app):
    create_task(client, "No details", "   ")
    assert fetch_tasks(app)[0]["description"] is None


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_blank_title_is_rejected(client, logged_in, app, title):
    response = create_task(client, title, "Keep me")
    assert response.status_code == 200
    assert b"Title is required." in response.data
    assert b"Keep me" in response.data
    assert fetch_tasks(app) == []


def test_title_length_limit(client, logged_in, app):
    response = create_task(client, "x" * 121, "Still here")
    assert b"Title must be 120 characters or fewer." in response.data
    assert b"Still here" in response.data
    assert fetch_tasks(app) == []

    create_task(client, "x" * 120)
    assert len(fetch_tasks(app)) == 1


def test_description_length_limit(client, logged_in, app):
    response = create_task(client, "Keep this title", "d" * 1001)
    assert b"Description must be 1000 characters or fewer." in response.data
    assert b'value="Keep this title"' in response.data
    assert fetch_tasks(app) == []

    create_task(client, "Long but allowed", "d" * 1000)
    assert len(fetch_tasks(app)) == 1


def test_task_content_is_html_escaped(client, logged_in):
    create_task(client, "<script>alert(1)</script>", "<b>bold</b>")
    html = dashboard_html(client)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ---------- Dashboard ----------

def test_empty_dashboard_shows_message(client, logged_in):
    html = dashboard_html(client)
    assert "You have no tasks yet" in html
    assert 'id="taskList"' not in html
    assert (stat(html, "Total"), stat(html, "Completed"), stat(html, "Remaining")) == (0, 0, 0)


def test_dashboard_lists_tasks_with_details(client, logged_in):
    create_task(client, "Write essay", "Five paragraphs")
    html = dashboard_html(client)
    assert "Write essay" in html
    assert "Five paragraphs" in html
    assert "Incomplete" in html
    assert re.search(r"Created \d{4}-\d{2}-\d{2}", html)
    assert "You have no tasks yet" not in html


def test_dashboard_statistics(client, logged_in, app):
    for title in ("One", "Two", "Three"):
        create_task(client, title)
    first_id = fetch_tasks(app)[0]["id"]
    post_with_token(client, f"/tasks/{first_id}/toggle")

    html = dashboard_html(client)
    assert stat(html, "Total") == 3
    assert stat(html, "Completed") == 1
    assert stat(html, "Remaining") == 2


def test_dashboard_order_incomplete_first_then_newest(client, logged_in, app):
    for title in ("Oldest", "Middle", "Newest"):
        create_task(client, title)
    newest_id = fetch_tasks(app)[2]["id"]
    post_with_token(client, f"/tasks/{newest_id}/toggle")

    assert task_titles(dashboard_html(client)) == ["Middle", "Oldest", "Newest"]


def test_dashboard_shows_only_own_tasks(client, other_users_task):
    create_task(client, "Alice's task")
    html = dashboard_html(client)
    assert "Alice&#39;s task" in html
    assert "Bob&#39;s private task" not in html
    assert stat(html, "Total") == 1


def test_dashboard_controls_present(client, logged_in, app):
    create_task(client)
    task_id = fetch_tasks(app)[0]["id"]
    html = dashboard_html(client)
    assert 'href="/tasks/new"' in html
    assert f'href="/tasks/{task_id}/edit"' in html
    assert f'action="/tasks/{task_id}/toggle"' in html
    assert "Mark Complete" in html


# ---------- Editing tasks ----------

def test_edit_page_prefills_values(client, logged_in, app):
    create_task(client, "Original title", "Original description")
    task_id = fetch_tasks(app)[0]["id"]
    response = client.get(f"/tasks/{task_id}/edit")
    assert response.status_code == 200
    assert b"<title>Edit Task - Personal Task Tracker</title>" in response.data
    assert b'value="Original title"' in response.data
    assert b">Original description</textarea>" in response.data
    assert f'action="/tasks/{task_id}/edit"'.encode() in response.data


def test_edit_saves_changes(client, logged_in, app):
    create_task(client, "Original title", "Original description")
    task_id = fetch_tasks(app)[0]["id"]
    response = post_with_token(client, f"/tasks/{task_id}/edit", {
        "title": "Updated title", "description": "Updated description",
    })
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"

    task = fetch_task(app, task_id)
    assert task["title"] == "Updated title"
    assert task["description"] == "Updated description"
    assert b"Task updated." in client.get("/dashboard").data


def test_edit_validation_keeps_original_task(client, logged_in, app):
    create_task(client, "Original title")
    task_id = fetch_tasks(app)[0]["id"]
    response = post_with_token(client, f"/tasks/{task_id}/edit", {
        "title": "   ", "description": "New text",
    })
    assert response.status_code == 200
    assert b"Title is required." in response.data
    assert b"New text" in response.data
    assert fetch_task(app, task_id)["title"] == "Original title"


def test_edit_rejects_long_values(client, logged_in, app):
    create_task(client, "Original title")
    task_id = fetch_tasks(app)[0]["id"]
    response = post_with_token(client, f"/tasks/{task_id}/edit", {
        "title": "t" * 121, "description": "d" * 1001,
    })
    assert b"Title must be 120 characters or fewer." in response.data
    assert b"Description must be 1000 characters or fewer." in response.data
    assert fetch_task(app, task_id)["title"] == "Original title"


# ---------- Completing tasks ----------

def test_toggle_marks_complete_and_incomplete(client, logged_in, app):
    create_task(client)
    task_id = fetch_tasks(app)[0]["id"]

    response = post_with_token(client, f"/tasks/{task_id}/toggle")
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    assert fetch_task(app, task_id)["completed"] == 1
    html = dashboard_html(client)
    assert "Mark Incomplete" in html
    assert "task-complete" in html

    post_with_token(client, f"/tasks/{task_id}/toggle")
    assert fetch_task(app, task_id)["completed"] == 0


# ---------- Deleting tasks ----------

def test_delete_removes_only_that_task(client, logged_in, app):
    create_task(client, "Keep me")
    create_task(client, "Delete me")
    keep_id, delete_id = [task["id"] for task in fetch_tasks(app)]

    response = post_with_token(client, f"/tasks/{delete_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    assert [task["id"] for task in fetch_tasks(app)] == [keep_id]

    html = dashboard_html(client)
    assert "Deleted &#34;Delete me&#34;." in html
    assert task_titles(html) == ["Keep me"]


# ---------- Delete confirmation modal ----------

def test_bootstrap_bundle_loaded_on_dashboard(client, logged_in):
    assert "bootstrap.bundle.min.js" in dashboard_html(client)


def test_delete_modal_markup(client, logged_in, app):
    create_task(client, "Modal task")
    task_id = fetch_tasks(app)[0]["id"]
    html = dashboard_html(client)

    # The Delete button opens this task's modal instead of deleting directly.
    assert re.search(
        rf'data-bs-toggle="modal" data-bs-target="#deleteModal-{task_id}"', html)

    modal = re.search(
        rf'<div class="modal fade" id="deleteModal-{task_id}".*?</form>', html, re.S).group(0)
    assert "Modal task" in modal
    assert 'data-bs-dismiss="modal">Cancel</button>' in modal
    assert f'<form method="post" action="/tasks/{task_id}/delete">' in modal
    assert f'name="csrf_token" value="{get_csrf_token(client)}"' in modal
    assert "Confirm Delete" in modal


def test_each_task_has_its_own_modal(client, logged_in, app):
    for title in ("First", "Second", "Third"):
        create_task(client, title)
    html = dashboard_html(client)

    modal_ids = re.findall(r'<div class="modal fade" id="deleteModal-(\d+)"', html)
    targets = re.findall(r'data-bs-target="#deleteModal-(\d+)"', html)
    assert len(modal_ids) == 3
    assert len(set(modal_ids)) == 3
    assert sorted(targets) == sorted(modal_ids)

    for task in fetch_tasks(app):
        modal = re.search(
            rf'id="deleteModal-{task["id"]}".*?</form>', html, re.S).group(0)
        assert task["title"] in modal
        assert f'action="/tasks/{task["id"]}/delete"' in modal


def test_no_modal_when_no_tasks(client, logged_in):
    assert "deleteModal-" not in dashboard_html(client)


# ---------- CSRF and HTTP methods ----------

@pytest.mark.parametrize("action", ["toggle", "delete", "edit"])
@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_task_posts_reject_bad_csrf(client, logged_in, app, action, token):
    create_task(client, "Protected")
    task_id = fetch_tasks(app)[0]["id"]
    data = {"title": "Hacked"}
    if token is not None:
        data["csrf_token"] = token
    response = client.post(f"/tasks/{task_id}/{action}", data=data)
    assert response.status_code == 400
    task = fetch_task(app, task_id)
    assert task["title"] == "Protected"
    assert task["completed"] == 0


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_create_rejects_bad_csrf(client, logged_in, app, token):
    data = {"title": "Forged"}
    if token is not None:
        data["csrf_token"] = token
    assert client.post("/tasks/new", data=data).status_code == 400
    assert fetch_tasks(app) == []


@pytest.mark.parametrize("action", ["toggle", "delete"])
def test_get_cannot_modify_tasks(client, logged_in, app, action):
    create_task(client)
    task_id = fetch_tasks(app)[0]["id"]
    assert client.get(f"/tasks/{task_id}/{action}").status_code == 405
    task = fetch_task(app, task_id)
    assert task is not None
    assert task["completed"] == 0


# ---------- Ownership ----------

def test_cannot_view_other_users_task_edit_page(client, other_users_task):
    response = client.get(f"/tasks/{other_users_task}/edit")
    assert response.status_code == 404
    assert b"Bob&#39;s private task" not in response.data


def test_cannot_edit_other_users_task(client, app, other_users_task):
    response = post_with_token(client, f"/tasks/{other_users_task}/edit", {
        "title": "Hijacked", "description": "",
    })
    assert response.status_code == 404
    assert fetch_task(app, other_users_task)["title"] == "Bob's private task"


def test_cannot_toggle_other_users_task(client, app, other_users_task):
    response = post_with_token(client, f"/tasks/{other_users_task}/toggle")
    assert response.status_code == 404
    assert fetch_task(app, other_users_task)["completed"] == 0


def test_cannot_delete_other_users_task(client, app, other_users_task):
    response = post_with_token(client, f"/tasks/{other_users_task}/delete")
    assert response.status_code == 404
    assert fetch_task(app, other_users_task) is not None


@pytest.mark.parametrize("method, action", [
    ("get", "edit"), ("post", "edit"), ("post", "toggle"), ("post", "delete"),
])
def test_missing_task_returns_404(client, logged_in, method, action):
    if method == "get":
        response = client.get(f"/tasks/9999/{action}")
    else:
        response = post_with_token(client, f"/tasks/9999/{action}", {"title": "x"})
    assert response.status_code == 404
    assert b"Page Not Found" in response.data


def test_non_numeric_task_id_returns_404(client, logged_in):
    assert client.get("/tasks/abc/edit").status_code == 404


# ---------- Public pages ----------

@pytest.mark.parametrize("path", [page[0] for page in PUBLIC_PAGES])
def test_public_pages_do_not_mention_unsupported_features(client, path):
    html = client.get(path).get_data(as_text=True).lower()
    for phrase in ("due date", "deadline", "planned", "coming in", "not yet available"):
        assert phrase not in html


def test_features_page_marks_everything_available(client):
    html = client.get("/features").get_data(as_text=True)
    assert html.count(">Available</span>") == 6
    assert "Planned" not in html
