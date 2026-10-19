# INF601 - Advanced Programming in Python
# Nicholas Pollard
# Mini Project 5

"""Smoke tests for the Personal Task Tracker."""

import re

import pytest

from app import create_app

# Each public page: (path, expected <title> prefix, text unique to that page).
PUBLIC_PAGES = [
    ("/", "Home", b"Personal Task Tracker"),
    ("/about", "About", b"About the Task Tracker"),
    ("/features", "Features", b"Track Progress"),
    ("/help", "Help", b"Frequently Asked Questions"),
]


def nav_links(html):
    """Return the href values of the links inside the main navigation menu."""
    nav = re.search(r'<div class="collapse navbar-collapse" id="mainNav">(.*?)</div>',
                    html, re.S).group(1)
    return re.findall(r'href="([^"]+)"', nav)


def test_app_is_in_testing_mode():
    """The factory should apply the test configuration."""
    assert create_app({"TESTING": True}).testing


def test_homepage_loads(client):
    """The homepage should respond successfully and render the base template."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Personal Task Tracker" in response.data
    assert b"bootstrap" in response.data


@pytest.mark.parametrize("path, title, content", PUBLIC_PAGES)
def test_public_page_renders(client, path, title, content):
    """Each public page should return 200 with its own title and content."""
    response = client.get(path)
    assert response.status_code == 200
    assert f"<title>{title} - Personal Task Tracker</title>".encode() in response.data
    assert content in response.data


@pytest.mark.parametrize("path", [page[0] for page in PUBLIC_PAGES])
def test_page_uses_shared_layout(client, path):
    """Every page should inherit the navbar, footer, and assets from base.html."""
    html = client.get(path).get_data(as_text=True)
    assert html.count("<html") == 1
    assert 'class="navbar' in html
    assert "INF601 Mini Project 5" in html
    assert "bootstrap.min.css" in html
    assert "bootstrap.bundle.min.js" in html
    assert "/static/css/style.css" in html


def test_navigation_contains_all_public_pages(client):
    """The navigation menu should link to every public page."""
    links = nav_links(client.get("/").get_data(as_text=True))
    assert links == [page[0] for page in PUBLIC_PAGES]


def test_navigation_links_resolve(client):
    """Every link in the navigation menu should load successfully."""
    for link in nav_links(client.get("/").get_data(as_text=True)):
        assert client.get(link).status_code == 200


@pytest.mark.parametrize("path", [page[0] for page in PUBLIC_PAGES])
def test_active_page_indicator(client, path):
    """Only the current page's nav link should be marked active."""
    html = client.get(path).get_data(as_text=True)
    active = re.findall(r'<a class="nav-link active" aria-current="page"\s+href="([^"]+)"', html)
    assert active == [path]


def test_static_stylesheet_is_served(client):
    """The custom stylesheet should be available."""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    response.close()


def test_unknown_page_returns_404(client):
    """Routes that do not exist should return 404."""
    assert client.get("/does-not-exist").status_code == 404
