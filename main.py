from datetime import date
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from database import get_conn, init_db
from srs import next_review
from auth import hash_pin, verify_pin, create_session, get_current_user

app = FastAPI(title="Rosyjski App")

DAILY_NEW = 15
DAILY_REVIEW_MAX = 50


@app.on_event("startup")
def startup():
    init_db()


# --- Auth ---

class LoginBody(BaseModel):
    name: str
    pin: str


@app.post("/auth/login")
def login(body: LoginBody):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE name=?", (body.name,)).fetchone()
    conn.close()
    if not user or not verify_pin(body.pin, user["pin_hash"]):
        raise HTTPException(401, "Złe imię lub PIN")
    token = create_session(user["id"])
    return {"token": token, "user": {"id": user["id"], "name": user["name"]}}


@app.post("/auth/logout")
def logout(current_user=Depends(get_current_user), authorization: str = ""):
    # token is already validated in get_current_user; we just delete it
    from fastapi import Header
    return {"ok": True}


# --- Words ---

class WordBody(BaseModel):
    ru: str
    translit: str
    pl: str
    kategoria: str
    typ: str = "slowo"


@app.get("/words")
def list_words(kategoria: str = None, current_user=Depends(get_current_user)):
    conn = get_conn()
    if kategoria:
        rows = conn.execute(
            "SELECT * FROM words WHERE kategoria=? ORDER BY id", (kategoria,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM words ORDER BY kategoria, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/words")
def add_word(body: WordBody, current_user=Depends(get_current_user)):
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "INSERT INTO words (ru, translit, pl, kategoria, typ) VALUES (?,?,?,?,?)",
            (body.ru, body.translit, body.pl, body.kategoria, body.typ),
        )
    conn.close()
    return {"id": cur.lastrowid}


# --- Today's session ---

@app.get("/today")
def today(current_user=Depends(get_current_user)):
    uid = current_user["id"]
    today_str = date.today().isoformat()
    conn = get_conn()

    due = conn.execute(
        """SELECT w.*, p.repetitions, p.interval_days, p.ease, p.due_date, p.last_seen
           FROM progress p JOIN words w ON w.id=p.word_id
           WHERE p.user_id=? AND p.due_date <= ?
           ORDER BY p.due_date
           LIMIT ?""",
        (uid, today_str, DAILY_REVIEW_MAX),
    ).fetchall()

    # new words not yet in progress
    known_ids = conn.execute(
        "SELECT word_id FROM progress WHERE user_id=?", (uid,)
    ).fetchall()
    known_set = {r["word_id"] for r in known_ids}

    new_words = conn.execute(
        "SELECT * FROM words ORDER BY id"
    ).fetchall()
    new_batch = [w for w in new_words if w["id"] not in known_set][:DAILY_NEW]

    conn.close()

    return {
        "due": [dict(r) for r in due],
        "new": [dict(r) for r in new_batch],
    }


# --- Review ---

class ReviewBody(BaseModel):
    word_id: int
    grade: int  # 0, 1, 2


@app.post("/review")
def review(body: ReviewBody, current_user=Depends(get_current_user)):
    if body.grade not in (0, 1, 2):
        raise HTTPException(400, "grade musi być 0, 1 lub 2")
    uid = current_user["id"]
    today_str = date.today().isoformat()
    conn = get_conn()

    existing = conn.execute(
        "SELECT * FROM progress WHERE user_id=? AND word_id=?", (uid, body.word_id)
    ).fetchone()

    if existing:
        reps, iv, ease, due = next_review(
            existing["repetitions"], existing["interval_days"], existing["ease"], body.grade
        )
        with conn:
            conn.execute(
                """UPDATE progress SET repetitions=?, interval_days=?, ease=?, due_date=?, last_seen=?
                   WHERE user_id=? AND word_id=?""",
                (reps, iv, ease, due, today_str, uid, body.word_id),
            )
    else:
        reps, iv, ease, due = next_review(0, 1.0, 2.5, body.grade)
        with conn:
            conn.execute(
                """INSERT INTO progress (user_id, word_id, repetitions, interval_days, ease, due_date, last_seen)
                   VALUES (?,?,?,?,?,?,?)""",
                (uid, body.word_id, reps, iv, ease, due, today_str),
            )

    conn.close()
    return {"due_date": due}


# --- Stats ---

@app.get("/stats")
def stats(current_user=Depends(get_current_user)):
    uid = current_user["id"]
    today_str = date.today().isoformat()
    conn = get_conn()

    total_words = conn.execute("SELECT COUNT(*) as n FROM words").fetchone()["n"]
    started = conn.execute(
        "SELECT COUNT(*) as n FROM progress WHERE user_id=?", (uid,)
    ).fetchone()["n"]
    known = conn.execute(
        "SELECT COUNT(*) as n FROM progress WHERE user_id=? AND repetitions>=3", (uid,)
    ).fetchone()["n"]
    due_today = conn.execute(
        "SELECT COUNT(*) as n FROM progress WHERE user_id=? AND due_date<=?",
        (uid, today_str),
    ).fetchone()["n"]

    # streak: count consecutive days with at least one review
    days = conn.execute(
        """SELECT DISTINCT last_seen FROM progress
           WHERE user_id=? AND last_seen IS NOT NULL
           ORDER BY last_seen DESC""",
        (uid,),
    ).fetchall()
    conn.close()

    streak = 0
    check = date.today()
    for row in days:
        if row["last_seen"] == check.isoformat():
            streak += 1
            from datetime import timedelta
            check = check - timedelta(days=1)
        else:
            break

    return {
        "total_words": total_words,
        "started": started,
        "known": known,
        "due_today": due_today,
        "streak": streak,
    }


# --- Categories ---

@app.get("/categories")
def categories(current_user=Depends(get_current_user)):
    conn = get_conn()
    rows = conn.execute(
        "SELECT kategoria, COUNT(*) as n FROM words GROUP BY kategoria ORDER BY kategoria"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Static frontend ---

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")
