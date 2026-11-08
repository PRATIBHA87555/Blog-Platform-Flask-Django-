"""Inkwell - a beautiful blog platform built with Flask.

Run:  python app.py   (then open http://127.0.0.1:5000)
"""
import html as html_lib
import math
import os
import re
import secrets
import sqlite3
import threading
import webbrowser
from collections import Counter
from datetime import datetime
from functools import wraps

import bleach
import markdown
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

from seed_data import DEMO_BIO, SEED_POSTS

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

PER_PAGE = 6
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def _secret_key():
    """Use SECRET_KEY from the environment, else create and remember a random one."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = os.path.join(INSTANCE_DIR, "secret.key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app = Flask(__name__)
app.config.update(
    SECRET_KEY=_secret_key(),
    DATABASE=os.path.join(INSTANCE_DIR, "blog.db"),
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=1024 * 1024,
)

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    views INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, post_id)
);
"""

_ready = set()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and, on a brand-new database, add a demo account and posts."""
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        uid = db.execute(
            "INSERT INTO users (username, password_hash, bio) VALUES (?, ?, ?)",
            ("demo", generate_password_hash("demo1234"), DEMO_BIO),
        ).lastrowid
        for i, (title, tags, content) in enumerate(SEED_POSTS):
            db.execute(
                "INSERT INTO posts (user_id, title, content, tags, created_at, updated_at, views)"
                " VALUES (?, ?, ?, ?, datetime('now', ?), datetime('now', ?), ?)",
                (uid, title, content, tags, f"-{i * 2} days", f"-{i * 2} days", 40 + i * 17),
            )
    db.commit()
    db.close()


POST_SELECT = """
SELECT p.*, u.username,
       (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS likes,
       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comments
FROM posts p JOIN users u ON u.id = p.user_id
"""


def get_post_or_404(post_id):
    post = get_db().execute(POST_SELECT + " WHERE p.id = ?", (post_id,)).fetchone()
    if post is None:
        abort(404)
    return post


# --------------------------------------------------------------------------
# Markdown + template helpers
# --------------------------------------------------------------------------
ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "strong", "em", "b", "i", "ul", "ol", "li",
    "blockquote", "code", "pre", "a", "img", "table", "thead", "tbody", "tr", "th", "td",
]
ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt", "title"], "code": ["class"]}


def render_md(text):
    """Markdown -> sanitized HTML (scripts and unsafe markup are stripped)."""
    raw = markdown.markdown(text or "", extensions=["fenced_code", "tables", "nl2br"])
    clean = bleach.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                         protocols=["http", "https", "mailto"], strip=True)
    return Markup(clean)


@app.template_filter("md")
def md_filter(text):
    return render_md(text)


@app.template_filter("excerpt")
def excerpt_filter(text, length=150):
    plain = bleach.clean(markdown.markdown(text or ""), tags=[], strip=True)
    plain = " ".join(html_lib.unescape(plain).split())
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"


@app.template_filter("reading_time")
def reading_time_filter(text):
    return max(1, math.ceil(len((text or "").split()) / 200))


@app.template_filter("date")
def date_filter(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y")
    except (TypeError, ValueError):
        return value


@app.template_filter("taglist")
def taglist_filter(value):
    return [t for t in (value or "").split(",") if t]


@app.template_filter("cover")
def cover_filter(key):
    """A unique, pretty gradient for every post / user."""
    n = key if isinstance(key, int) else sum(ord(c) * (i + 3) for i, c in enumerate(str(key)))
    h1 = (n * 47 + 230) % 360
    h2 = (h1 + 55) % 360
    return f"linear-gradient(135deg, hsl({h1} 80% 58%), hsl({h2} 85% 52%))"


def normalize_tags(raw):
    seen = []
    for t in (raw or "").split(","):
        t = re.sub(r"[^a-z0-9-]", "", t.strip().lower().replace(" ", "-"))[:24]
        if t and t not in seen:
            seen.append(t)
    return ",".join(seen[:5])


def popular_tags(db, limit=10):
    counter = Counter()
    for row in db.execute("SELECT tags FROM posts"):
        counter.update(t for t in row["tags"].split(",") if t)
    return counter.most_common(limit)


# --------------------------------------------------------------------------
# Security: CSRF protection, login handling
# --------------------------------------------------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def ensure_db_and_csrf():
    path = app.config["DATABASE"]
    if path not in _ready:
        init_db()
        _ready.add(path)
    if request.method == "POST":
        token = session.get("_csrf", "")
        sent = request.form.get("_csrf", "")
        if not token or not secrets.compare_digest(token, sent):
            abort(400)


@app.before_request
def load_user():
    uid = session.get("user_id")
    g.user = None
    if uid:
        g.user = get_db().execute(
            "SELECT id, username, bio, created_at FROM users WHERE id = ?", (uid,)
        ).fetchone()
        if g.user is None:
            session.pop("user_id", None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


@app.errorhandler(400)
def bad_request(_e):
    return render_template("error.html", code=400,
                           message="That request could not be verified. Go back, refresh and try again."), 400


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, message="You are not allowed to do that."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, message="We could not find that page."), 404


@app.errorhandler(413)
def too_large(_e):
    return render_template("error.html", code=413, message="That submission is too large."), 413


# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    tag = re.sub(r"[^a-z0-9-]", "", request.args.get("tag", "").strip().lower())
    page = max(request.args.get("page", 1, type=int), 1)

    where, params = [], []
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where.append("(p.title LIKE ? ESCAPE '\\' OR p.content LIKE ? ESCAPE '\\')")
        params += [like, like]
    if tag:
        where.append("(',' || p.tags || ',') LIKE ?")
        params.append(f"%,{tag},%")
    clause = (" WHERE " + " AND ".join(where)) if where else ""

    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM posts p" + clause, params).fetchone()[0]
    pages = max(math.ceil(total / PER_PAGE), 1)
    page = min(page, pages)
    posts = db.execute(
        POST_SELECT + clause + " ORDER BY p.created_at DESC, p.id DESC LIMIT ? OFFSET ?",
        params + [PER_PAGE, (page - 1) * PER_PAGE],
    ).fetchall()
    return render_template("index.html", posts=posts, q=q, tag=tag, page=page, pages=pages,
                           total=total, tags=popular_tags(db))


@app.route("/post/<int:post_id>")
def post_view(post_id):
    db = get_db()
    get_post_or_404(post_id)
    db.execute("UPDATE posts SET views = views + 1 WHERE id = ?", (post_id,))
    db.commit()
    post = get_post_or_404(post_id)
    comments = db.execute(
        "SELECT c.*, u.username FROM comments c JOIN users u ON u.id = c.user_id"
        " WHERE c.post_id = ? ORDER BY c.created_at, c.id", (post_id,)).fetchall()
    liked = False
    if g.user:
        liked = db.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?",
                           (g.user["id"], post_id)).fetchone() is not None
    return render_template("post.html", post=post, comments=comments, liked=liked)


@app.route("/u/<username>")
def profile(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None:
        abort(404)
    posts = db.execute(POST_SELECT + " WHERE p.user_id = ? ORDER BY p.created_at DESC, p.id DESC",
                       (user["id"],)).fetchall()
    stats = {
        "posts": len(posts),
        "likes": sum(p["likes"] for p in posts),
        "views": sum(p["views"] for p in posts),
    }
    return render_template("profile.html", profile=user, posts=posts, stats=stats)


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3-20 characters: letters, numbers or underscore."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        if error is None:
            db = get_db()
            try:
                cur = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                 (username, generate_password_hash(password)))
                db.commit()
            except sqlite3.IntegrityError:
                error = "That username is already taken."
            else:
                session.clear()
                session["user_id"] = cur.lastrowid
                flash(f"Welcome to Inkwell, {username}!", "success")
                return redirect(url_for("index"))
        flash(error, "error")
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(safe_next(request.args.get("next")) or url_for("index"))
        flash("Wrong username or password.", "error")
    return render_template("auth.html", mode="login")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def read_post_form():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    tags = normalize_tags(request.form.get("tags", ""))
    error = None
    if not title:
        error = "Please give your post a title."
    elif len(title) > 120:
        error = "Title must be 120 characters or fewer."
    elif len(content) < 10:
        error = "Your post is a bit short. Write at least a sentence or two."
    elif len(content) > 50000:
        error = "Your post is too long (50,000 characters max)."
    return title, content, tags, error


@app.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title, content, tags, error = read_post_form()
        if error:
            flash(error, "error")
            return render_template("editor.html", post=None,
                                   form={"title": title, "content": content, "tags": tags})
        db = get_db()
        cur = db.execute("INSERT INTO posts (user_id, title, content, tags) VALUES (?, ?, ?, ?)",
                         (g.user["id"], title, content, tags))
        db.commit()
        flash("Your post is live!", "success")
        return redirect(url_for("post_view", post_id=cur.lastrowid))
    return render_template("editor.html", post=None, form={"title": "", "content": "", "tags": ""})


def owned_post_or_403(post_id):
    post = get_post_or_404(post_id)
    if post["user_id"] != g.user["id"]:
        abort(403)
    return post


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = owned_post_or_403(post_id)
    if request.method == "POST":
        title, content, tags, error = read_post_form()
        if error:
            flash(error, "error")
            return render_template("editor.html", post=post,
                                   form={"title": title, "content": content, "tags": tags})
        db = get_db()
        db.execute("UPDATE posts SET title = ?, content = ?, tags = ?, updated_at = datetime('now')"
                   " WHERE id = ?", (title, content, tags, post_id))
        db.commit()
        flash("Post updated.", "success")
        return redirect(url_for("post_view", post_id=post_id))
    return render_template("editor.html", post=post,
                           form={"title": post["title"], "content": post["content"],
                                 "tags": post["tags"].replace(",", ", ")})


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    owned_post_or_403(post_id)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("index"))


@app.route("/preview", methods=["POST"])
@login_required
def preview():
    return jsonify(html=str(render_md(request.form.get("content", ""))))


# --------------------------------------------------------------------------
# Engagement
# --------------------------------------------------------------------------
@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    get_post_or_404(post_id)
    db = get_db()
    existing = db.execute("SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?",
                          (g.user["id"], post_id)).fetchone()
    if existing:
        db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (g.user["id"], post_id))
    else:
        db.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (g.user["id"], post_id))
    db.commit()
    return redirect(url_for("post_view", post_id=post_id) + "#actions")


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def comment_post(post_id):
    get_post_or_404(post_id)
    body = request.form.get("body", "").strip()
    if not body or len(body) > 1000:
        flash("Comments must be between 1 and 1000 characters.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO comments (post_id, user_id, body) VALUES (?, ?, ?)",
                   (post_id, g.user["id"], body))
        db.commit()
        flash("Comment added.", "success")
    return redirect(url_for("post_view", post_id=post_id) + "#comments")


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    db = get_db()
    row = db.execute(
        "SELECT c.id, c.user_id, c.post_id, p.user_id AS post_owner FROM comments c"
        " JOIN posts p ON p.id = c.post_id WHERE c.id = ?", (comment_id,)).fetchone()
    if row is None:
        abort(404)
    if g.user["id"] not in (row["user_id"], row["post_owner"]):
        abort(403)
    db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    db.commit()
    flash("Comment removed.", "info")
    return redirect(url_for("post_view", post_id=row["post_id"]) + "#comments")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    _ready.add(app.config["DATABASE"])
    port = int(os.environ.get("PORT", 5000))
    if not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"\n  Inkwell is running at http://127.0.0.1:{port}   (press Ctrl+C to stop)\n"
          "  Demo login ->  username: demo   password: demo1234\n")
    app.run(host="127.0.0.1", port=port, debug=False)
