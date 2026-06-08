import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException
from database import get_conn

SESSION_DAYS = 30


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, hashed: str) -> bool:
    return bcrypt.checkpw(pin.encode(), hashed.encode())


def create_session(user_id: int) -> str:
    token = str(uuid.uuid4())
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )
    conn.close()
    return token


def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Brak tokenu")
    token = authorization.removeprefix("Bearer ")
    conn = get_conn()
    row = conn.execute(
        "SELECT s.user_id, s.expires_at, u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(401, "Nieważny token")
    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(401, "Sesja wygasła")
    return {"id": row["user_id"], "name": row["name"]}
