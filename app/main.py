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
