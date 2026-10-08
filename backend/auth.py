"""Create-account / log-in for Campus Customs.

Passwords are never stored. Each one is run through PBKDF2-HMAC-SHA256 with a random
per-user salt and 600,000 iterations, saved as `pbkdf2_sha256$<iterations>$<salt>$<hex hash>`.
Seed users use the older `pbkdf2_sha256$<salt>$<hex hash>` format (120,000 iterations); they
still log in and are upgraded to the stronger format on success. Sessions use a signed,
HttpOnly cookie.
"""

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

PBKDF2_ITERATIONS = 600_000  # OWASP 2023+ recommendation for PBKDF2-HMAC-SHA256
LEGACY_ITERATIONS = 120_000  # used by the seed users' 3-part hashes
SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
SECRET_FILE = Path(__file__).resolve().parent / ".session_secret"

router = APIRouter(prefix="/api/auth")
_failed_logins: dict[str, list[float]] = defaultdict(list)


def _session_secret() -> bytes:
    """Secret for signing session cookies: SESSION_SECRET env var, else a local gitignored file."""
    if env := os.getenv("SESSION_SECRET"):
        return env.encode()
    if not SECRET_FILE.exists():
        SECRET_FILE.write_text(secrets.token_hex(32))
        SECRET_FILE.chmod(0o600)
    return SECRET_FILE.read_text().strip().encode()


SECRET = _session_secret()


# ---------- password hashing ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def _parse_hash(stored: str) -> tuple[int, str, str] | None:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256" and parts[1].isdigit():
        return int(parts[1]), parts[2], parts[3]
    if len(parts) == 3 and parts[0] == "pbkdf2_sha256":
        return LEGACY_ITERATIONS, parts[1], parts[2]
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse_hash(stored)
    if parsed is None:
        return False
    iterations, salt, expected = parsed
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return hmac.compare_digest(digest.hex(), expected)  # constant-time compare


def needs_rehash(stored: str) -> bool:
    parsed = _parse_hash(stored)
    return parsed is None or parsed[0] < PBKDF2_ITERATIONS


# Used when the email doesn't exist so response time doesn't reveal which emails are registered.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------- sessions ----------

def _sign(payload: str) -> str:
    return hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_session(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_TTL_SECONDS}"
    token = f"{payload}.{_sign(payload)}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def read_session(cookie: str | None) -> int | None:
    if not cookie:
        return None
    try:
        user_id, expires, sig = base64.urlsafe_b64decode(cookie.encode()).decode().split(".")
    except Exception:
        return None
    if not hmac.compare_digest(sig, _sign(f"{user_id}.{expires}")) or int(expires) < time.time():
        return None
    return int(user_id)


def _set_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE, make_session(user_id), max_age=SESSION_TTL_SECONDS,
        httponly=True, samesite="lax", secure=False,  # set secure=True when served over HTTPS
    )


def current_user_id(request: Request) -> int | None:
    return read_session(request.cookies.get(SESSION_COOKIE))


# ---------- routes ----------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _public_user(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "first_name": row["first_name"], "last_name": row["last_name"],
            "name": row["name"], "email": row["email"]}


class SignupIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


@router.post("/signup", status_code=201)
def signup(body: SignupIn, response: Response) -> dict:
    email = body.email.strip().lower()
    first, last = body.first_name.strip(), body.last_name.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if not first or not last:
        raise HTTPException(422, "First and last name are required.")
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    with _db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with that email already exists.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(body.password), first, last),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    _set_cookie(response, row["id"])
    return _public_user(row)


@router.post("/login")
def login(body: LoginIn, response: Response) -> dict:
    email = body.email.strip().lower()
    now = time.time()
    recent = [t for t in _failed_logins[email] if now - t < LOCKOUT_SECONDS]
    _failed_logins[email] = recent
    if len(recent) >= MAX_FAILED_LOGINS:
        raise HTTPException(429, "Too many failed attempts. Please try again in 15 minutes.")

    with _db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _failed_logins[email].append(now)
        raise HTTPException(401, "Invalid email or password.")  # same message either way
    _failed_logins.pop(email, None)
    if needs_rehash(row["password_hash"]):  # upgrade older/weaker hashes now that we know the password
        with _db() as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["id"]))
    _set_cookie(response, row["id"])
    return _public_user(row)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user_id = current_user_id(request)
    if user_id is None:
        raise HTTPException(401, "Not logged in.")
    with _db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "Not logged in.")
    return _public_user(row)
