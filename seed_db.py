"""
Run once to initialise the database: create tables, add users, import words.

  python seed_db.py

PINs are read from env vars PIN_MACIEJ / PIN_DOMINIKA (default 1234/5678).
Override on CLI:
  python seed_db.py --pin-maciej 9999 --pin-dominika 8888
"""
import json
import os
import argparse
from pathlib import Path

from database import init_db, get_conn
from auth import hash_pin

SEED_PATH = Path(__file__).parent / "seed" / "words.json"


def seed(pin_maciej: str, pin_dominika: str):
    init_db()
    conn = get_conn()

    users = [("Maciej", pin_maciej), ("Dominika", pin_dominika)]
    with conn:
        for name, pin in users:
            existing = conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()
            if existing:
                print(f"  user '{name}' already exists, skipping")
            else:
                conn.execute(
                    "INSERT INTO users (name, pin_hash) VALUES (?, ?)",
                    (name, hash_pin(pin)),
                )
                print(f"  created user '{name}'")

        words = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        inserted = 0
        for w in words:
            existing = conn.execute(
                "SELECT id FROM words WHERE ru=?", (w["ru"],)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO words (ru, translit, pl, kategoria, typ) VALUES (?,?,?,?,?)",
                    (w["ru"], w["translit"], w["pl"], w["kategoria"], w["typ"]),
                )
                inserted += 1
        print(f"  imported {inserted} words ({len(words) - inserted} already present)")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin-maciej", default=os.getenv("PIN_MACIEJ", "1234"))
    parser.add_argument("--pin-dominika", default=os.getenv("PIN_DOMINIKA", "5678"))
    args = parser.parse_args()
    seed(args.pin_maciej, args.pin_dominika)
