# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Entry point for running the Personal Task Tracker locally."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
