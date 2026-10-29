"""Local Vault SQLite store — includes phone numbers. Not shared with the Telegram bot DB."""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from vault.parser import VAULT_FIELDS, build_search_blob

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "vault.sqlite3"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS vault_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, gender TEXT, father_name TEXT, mother_name TEXT,
            dob TEXT, age INTEGER, nakshatram TEXT, padam TEXT, rashi TEXT,
            gotram TEXT, saka TEXT, birthplace TEXT, birthtime TEXT,
            education TEXT, location TEXT, phone TEXT,
            source_file TEXT NOT NULL, source_kind TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            search_blob TEXT,
            inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts USING fts5(search_blob)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_vault_star ON vault_profiles(nakshatram)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_vault_phone ON vault_profiles(phone)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_vault_gender ON vault_profiles(gender)")
    con.commit()
    return con


def fingerprint_for(profile: dict, source_file: str) -> str:
    key = "|".join(
        [
            (profile.get("name") or "").casefold().strip(),
            profile.get("dob") or "",
            profile.get("phone") or "",
            source_file,
        ]
    )
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def upsert_profile(profile: dict, *, source_file: str, source_kind: str) -> bool:
    blob = build_search_blob(profile)
    fp = fingerprint_for(profile, source_file)
    con = connect()
    try:
        existing = con.execute("SELECT id FROM vault_profiles WHERE fingerprint=?", (fp,)).fetchone()
        if existing:
            cols = list(VAULT_FIELDS) + ["source_file", "source_kind", "search_blob"]
            assignments = ", ".join(f"{c}=?" for c in cols)
            con.execute(
                f"UPDATE vault_profiles SET {assignments} WHERE id=?",
                [profile.get(f) for f in VAULT_FIELDS]
                + [source_file, source_kind, blob, existing["id"]],
            )
            pid = existing["id"]
            con.execute("DELETE FROM vault_fts WHERE rowid=?", (pid,))
            con.execute("INSERT INTO vault_fts(rowid, search_blob) VALUES (?, ?)", (pid, blob))
        else:
            placeholders = ",".join(["?"] * (len(VAULT_FIELDS) + 4))
            cur = con.execute(
                f"INSERT INTO vault_profiles({','.join(VAULT_FIELDS)}, source_file, source_kind, fingerprint, search_blob) "
                f"VALUES ({placeholders})",
                [profile.get(f) for f in VAULT_FIELDS] + [source_file, source_kind, fp, blob],
            )
            pid = cur.lastrowid
            con.execute("INSERT INTO vault_fts(rowid, search_blob) VALUES (?, ?)", (pid, blob))
        con.commit()
        return True
    finally:
        con.close()


def load_all() -> list[dict[str, Any]]:
    con = connect()
    try:
        return [dict(row) for row in con.execute("SELECT * FROM vault_profiles ORDER BY id DESC")]
    finally:
        con.close()


def count_profiles() -> int:
    con = connect()
    try:
        return int(con.execute("SELECT COUNT(*) FROM vault_profiles").fetchone()[0])
    finally:
        con.close()


def clear_all() -> int:
    con = connect()
    try:
        n = con.execute("SELECT COUNT(*) FROM vault_profiles").fetchone()[0]
        con.execute("DELETE FROM vault_fts")
        con.execute("DELETE FROM vault_profiles")
        con.commit()
        return int(n)
    finally:
        con.close()
