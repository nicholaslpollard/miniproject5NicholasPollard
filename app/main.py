# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""General page routes for the Personal Task Tracker."""

from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Display the homepage."""
    return render_template("index.html")


@bp.route("/about")
def about():
    """Display information about the purpose of the application."""
    return render_template("about.html")


@bp.route("/features")
def features():
    """Display the planned task-management features."""
    return render_template("features.html")


@bp.route("/help")
def help_page():
    """Display instructions for using the application."""
    return render_template("help.html")
