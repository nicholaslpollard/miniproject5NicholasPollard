# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""General page routes for the Personal Task Tracker."""

from flask import Blueprint, render_template

from .auth import login_required

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
    """Display the application's features."""
    return render_template("features.html")


@bp.route("/help")
def help_page():
    """Display instructions for using the application."""
    return render_template("help.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """Display the logged-in user's dashboard."""
    return render_template("dashboard.html")


@bp.app_errorhandler(400)
def bad_request(error):
    """Show a friendly page for rejected requests, such as invalid CSRF tokens."""
    return render_template("error.html", code=400, title="Bad Request",
                           message=error.description), 400


@bp.app_errorhandler(404)
def page_not_found(error):
    """Show a friendly page for unknown URLs."""
    return render_template("error.html", code=404, title="Page Not Found",
                           message="The page you requested does not exist."), 404


@bp.app_errorhandler(500)
def internal_error(error):
    """Show a friendly page instead of a stack trace when something fails."""
    return render_template("error.html", code=500, title="Something Went Wrong",
                           message="An unexpected error occurred. "
                                   "Please try again later."), 500
