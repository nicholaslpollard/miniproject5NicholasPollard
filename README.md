# Mini Project 5 - Personal Task Tracker

INF601 - Advanced Programming in Python  
Nicholas Pollard

## What this project does

This project is a Personal Task Tracker web application built with Flask, SQLite, Jinja2, and Bootstrap. Users can create an account, log in, and manage their own tasks from a personal dashboard.

The application allows users to:

- Register an account with a username, email address, and password.
- Log in and log out of their account.
- Create tasks with a title and optional description.
- View, edit, and delete their own tasks.
- Mark tasks complete or incomplete.
- View dashboard counts for total, completed, and remaining tasks.
- Filter the dashboard to show all tasks, active tasks, or completed tasks.
- Confirm task deletion using a Bootstrap modal.

Each account has its own task list. A logged-in user cannot access or modify tasks belonging to another user.

## How the application works

The application has public pages for Home, About, Features, and Help. Registration and Login have their own forms, and the Dashboard is available only after signing in. The Create Task and Edit Task pages also require login.

Tasks are displayed with incomplete tasks first, followed by completed tasks. Within those groups, newer tasks appear first. The dashboard has three filters:

- **All Tasks** - displays every task.
- **Active Tasks** - displays tasks that have not been completed.
- **Completed Tasks** - displays completed tasks.

The dashboard's Total, Completed, and Remaining counters continue to show overall totals even when a filter is selected. If there are no matching tasks, the page displays a message for that filter.

When deleting a task, the user must confirm the action in a Bootstrap modal before the delete request is submitted.

## Project structure

```text
miniproject5NicholasPollard/
    app/
        __init__.py
        auth.py
        csrf.py
        db.py
        main.py
        schema.sql
        tasks.py
        static/
            css/
                style.css
        templates/
            base.html
            index.html
            about.html
            features.html
            help.html
            dashboard.html
            error.html
            auth/
                login.html
                register.html
            tasks/
                task_form.html
    tests/
        conftest.py
        test_app.py
        test_auth.py
        test_db.py
        test_tasks.py
    .gitignore
    requirements.txt
    run.py
    README.md
```

- `app/__init__.py` creates and configures the Flask application and registers the blueprints.
- `app/main.py` handles the public pages and dashboard, including task filtering.
- `app/auth.py` handles registration, login, logout, and login protection.
- `app/tasks.py` handles creating, editing, completing, and deleting tasks.
- `app/db.py` manages SQLite connections and database initialization.
- `app/schema.sql` defines the database tables and their relationship.
- `app/csrf.py` validates the security tokens submitted with POST forms.
- `app/templates/` contains Jinja2 pages that share the layout in `base.html`.
- `app/static/css/style.css` contains the application's custom styling.
- `tests/` contains the automated tests.
- `run.py` starts the Flask development server.
- `requirements.txt` lists the required Python packages.

## Requirements

- Python 3.12 or a compatible Python 3 version
- Flask
- pytest (for running the tests)

The dependencies are listed in `requirements.txt`.

## Setup

These instructions use Windows PowerShell and should be run from the project folder.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install the requirements

```powershell
python -m pip install -r requirements.txt
```

### 3. Initialize the database

```powershell
flask --app app init-db
```

This creates the SQLite database in the `instance/` folder using the tables defined in `app/schema.sql`. The two tables are:

- `users` - stores account information, including a hashed password.
- `tasks` - stores task information and a `user_id` foreign key referencing the user who owns each task.

The foreign key uses `ON DELETE CASCADE`, so deleting a user also deletes that user's tasks. SQLite foreign-key enforcement is enabled when database connections are opened.

The `init-db` command uses `CREATE TABLE IF NOT EXISTS`, so running it again does not delete existing records. The application does not automatically reset the database when it starts.

The local SQLite database is excluded from Git by `.gitignore`.

## Running the application

With the virtual environment activated and the database initialized, start the Flask development server:

```powershell
python run.py
```

Open the following address in a web browser:

```text
http://127.0.0.1:5000/
```

Create an account using the Register page, then log in. From the dashboard, use **+ Add Task** to create a task. You can edit it, mark it complete or incomplete, or delete it after confirming in the modal. Use the filter buttons above the task list to switch between All Tasks, Active Tasks, and Completed Tasks.

Press `Ctrl + C` in the terminal to stop the server.

The application uses a development-only fallback for Flask's `SECRET_KEY`. A production environment must provide a long, random `SECRET_KEY` through an environment variable and use an appropriate production server instead of Flask's development server.

## Database and security

The application uses Python's built-in `sqlite3` module rather than an ORM. SQL statements that include user-provided values use parameter placeholders instead of inserting the values directly into the query.

Passwords are stored using Werkzeug's password hashing functions rather than as plain text. Flask sessions keep track of the signed-in user, and protected routes require login. All task lookups and changes are restricted to the current user's ID. POST forms also include CSRF tokens to protect against unauthorized form submissions.

## Testing

The project includes pytest tests for the public pages, database, authentication, and task operations. To run the test suite:

```powershell
python -m pytest -W error
```

The most recent full test run completed with:

```text
152 passed
```

The existing automated tests cover database relationships, registration and login, password hashing, CSRF validation, task creation and editing, completion, deletion, and checks that users cannot modify someone else's tasks.

I also tested the application in a browser by registering, logging in, creating tasks, editing them, completing them, and checking the delete-confirmation modal. After adding the dashboard filters, I checked that each filter displays the expected tasks and that the dashboard counts remain unchanged. The dashboard-filter improvement was manually verified; the 152-test result refers to the existing automated suite.

## AI Usage

### What I used AI for

I used Claude Code in Visual Studio Code to help develop the Flask application in stages. Claude helped set up the application structure, create the Jinja2 templates and Bootstrap styling, implement the SQLite database, build the registration and login system, and add task management and the delete-confirmation modal. Claude also created and ran automated tests, helped resolve issues found during development, and made the initial development commits.

### What I did myself

I set up the project folder, Python virtual environment, and Git repository, connected the repository to GitHub, reviewed the implementation as it was developed, and checked the test results at each stage. I ran the application in my browser and tested registration, login, task management, and the confirmation modal to make sure the features worked as expected.

### What I changed in the AI-generated code

After reviewing the completed application, I added task-status filtering to the dashboard. I updated `app/main.py` to read a status value from the URL and filter the tasks shown, while keeping the dashboard statistics based on all tasks. I also updated `app/templates/dashboard.html` with **All Tasks**, **Active Tasks**, and **Completed Tasks** buttons and messages for filters with no matching tasks.

After making those changes, I reran the existing test suite and confirmed that all tests still passed. I also checked the filtering behavior in the browser, including the highlighted filter buttons, the displayed tasks, and the overall task counts.
