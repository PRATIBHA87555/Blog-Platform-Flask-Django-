# Inkwell - a Flask blog platform

A modern blog with accounts, Markdown posts, live preview, tags, search, likes,
comments, user profiles and a light/dark theme. Uses SQLite (no database setup).

## Run it
1. Install Python 3.8+ (tick "Add Python to PATH" on Windows).
2. Windows: double-click `run.bat`.  Mac/Linux: `./run.sh`
   Or manually:
       pip install -r requirements.txt
       python app.py
3. Your browser opens at http://127.0.0.1:5000

Demo account: username `demo`, password `demo1234` (or sign up for your own).
The first run adds a few sample posts. Delete the `instance` folder to reset everything.

## Features
- Sign up / log in / log out (passwords are hashed)
- Write, edit and delete your own posts (Markdown + live preview)
- Tags, search, pagination, popular-tag filter
- Likes and comments (you can remove comments on your own posts)
- Profiles with stats, reading time, view counts
- Dark / light mode, responsive on mobile

## Security built in
CSRF protection on every form, sanitized Markdown (no script injection),
hashed passwords, owner-only edit/delete.

## Project layout
    app.py          routes and logic
    seed_data.py    sample posts
    templates/      HTML pages
    static/         style.css, app.js
    test_app.py     automated tests (python test_app.py)
