from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Optional, List, Dict

import bcrypt
from flask import Flask, render_template, request, redirect, url_for, abort, make_response
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)


SERVICES = [
    {"key": "cassa", "label": "Cassa", "emoji": "🏧", "path": "/cassa/"},
    {"key": "bar", "label": "Bar", "emoji": "🍺", "path": "/bar/"},
    {"key": "vending", "label": "Vending", "emoji": "🥤", "path": "/vending/"},
]


def get_env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


DB_PATH = get_env("PORTAL_DB", "/app/data/portal.db")
SECRET_KEY = get_env("SECRET_KEY", "change_me_in_production")
INIT_ADMIN_USER = get_env("INIT_ADMIN_USER", "admin")
INIT_ADMIN_PASSWORD = get_env("INIT_ADMIN_PASSWORD", "admin")


app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password TEXT NOT NULL,
              role TEXT DEFAULT 'operator'
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions (
              user_id INTEGER REFERENCES users(id),
              service TEXT,
              PRIMARY KEY (user_id, service)
            );
            """
        )

        cur = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role='admin'")
        n_admin = int(cur.fetchone()["n"])
        if n_admin == 0:
            pw_hash = bcrypt.hashpw(INIT_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')",
                (INIT_ADMIN_USER, pw_hash),
            )


@app.before_request
def _ensure_db():
    init_db()


class User(UserMixin):
    def __init__(self, user_id: int, username: str, role: str):
        self.id = str(user_id)
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    with db() as conn:
        row = conn.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return None
        return User(row["id"], row["username"], row["role"])


def user_has_permission(user_id: int, service: str) -> bool:
    if service not in {s["key"] for s in SERVICES}:
        return False

    with db() as conn:
        row = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return False
        if row["role"] == "admin":
            return True
        p = conn.execute(
            "SELECT 1 FROM permissions WHERE user_id=? AND service=?",
            (user_id, service),
        ).fetchone()
        return p is not None


def allowed_services_for_user(user_id: int) -> List[Dict]:
    allowed = []
    for svc in SERVICES:
        if user_has_permission(user_id, svc["key"]):
            allowed.append(svc)
    return allowed


@app.get("/")
@login_required
def dashboard():
    services = allowed_services_for_user(int(current_user.id))
    return render_template("dashboard.html", services=services, user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        next_url = request.args.get("next", "/")
        return render_template("login.html", next=next_url)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or "/"

    with db() as conn:
        row = conn.execute("SELECT id, username, password, role FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return render_template("login.html", next=next_url, error="Credenziali non valide")

        ok = bcrypt.checkpw(password.encode(), row["password"].encode())
        if not ok:
            return render_template("login.html", next=next_url, error="Credenziali non valide")

        user = User(row["id"], row["username"], row["role"])
        login_user(user)

    if not next_url.startswith("/"):
        next_url = "/"
    return redirect(next_url)


@app.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.get("/service/<service>")
@login_required
def open_service(service: str):
    if not user_has_permission(int(current_user.id), service):
        abort(403)
    svc = next((s for s in SERVICES if s["key"] == service), None)
    if not svc:
        abort(404)
    return render_template("service.html", service=svc)


@app.get("/__auth")
def auth_request():
    service = request.headers.get("X-Service", "")
    if not current_user.is_authenticated:
        return ("", 401)
    if user_has_permission(int(current_user.id), service):
        return ("", 200)
    return ("", 403)


@app.get("/admin")
@login_required
def admin():
    if getattr(current_user, "role", "operator") != "admin":
        abort(403)

    with db() as conn:
        users = conn.execute("SELECT id, username, role FROM users ORDER BY id ASC").fetchall()
        perms = conn.execute("SELECT user_id, service FROM permissions").fetchall()

    perms_map = {}
    for p in perms:
        perms_map.setdefault(int(p["user_id"]), set()).add(p["service"])

    return render_template(
        "admin.html",
        users=users,
        services=SERVICES,
        perms_map=perms_map,
        init_admin_user=INIT_ADMIN_USER,
    )


@app.post("/admin/users")
@login_required
def admin_create_user():
    if getattr(current_user, "role", "operator") != "admin":
        abort(403)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    role = request.form.get("role") or "operator"

    if not username or not password:
        return redirect(url_for("admin"))

    if role not in ("admin", "operator"):
        role = "operator"

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, pw_hash, role),
            )
        except sqlite3.IntegrityError:
            pass

    return redirect(url_for("admin"))


@app.post("/admin/users/<int:user_id>/permissions")
@login_required
def admin_set_permissions(user_id: int):
    if getattr(current_user, "role", "operator") != "admin":
        abort(403)

    selected = set(request.form.getlist("services"))
    valid = {s["key"] for s in SERVICES}
    selected = {s for s in selected if s in valid}

    with db() as conn:
        conn.execute("DELETE FROM permissions WHERE user_id=?", (user_id,))
        for svc in selected:
            conn.execute("INSERT INTO permissions (user_id, service) VALUES (?, ?)", (user_id, svc))

    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
