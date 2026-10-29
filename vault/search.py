"""Filter + full-text search over Vault profiles (full details, including phone)."""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from core import PLACE_ALIASES, RASHI_ALIASES, GOTRAM_ALIASES, SAKA_ALIASES, canonical, get_age
from vault.db import connect
from vault.parser import GENDER_ALIASES, STAR_ALIASES_VAULT


def _compact(s: str) -> str:
    return re.sub(r"[\s\-_/.,]+", "", s.casefold())


def _contains(hay: str | None, needle: str | None) -> bool:
    if not needle or not str(needle).strip():
        return True
    if not hay:
        return False
    return _compact(needle) in _compact(str(hay)) or needle.casefold() in str(hay).casefold()


def _exact_alias(hay: str | None, needle: str | None, aliases: dict | None) -> bool:
    if not needle or not str(needle).strip():
        return True
    if not hay:
        return False
    if aliases:
        return canonical(str(hay), aliases) == canonical(str(needle), aliases)
    return _compact(str(hay)) == _compact(str(needle))


def search_profiles(
    *,
    query: str = "",
    gender: str = "",
    name: str = "",
    father_name: str = "",
    mother_name: str = "",
    stars: str = "",
    padam: str = "",
    rashi: str = "",
    gotram: str = "",
    saka: str = "",
    birthplace: str = "",
    education: str = "",
    location: str = "",
    phone: str = "",
    min_age: int | None = None,
    max_age: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    con = connect()
    try:
        rows: list[sqlite3.Row]
        q = (query or "").strip()
        if q:
            # FTS5: quote tokens loosely; fall back to LIKE if MATCH fails.
            try:
                safe = " ".join(re.findall(r"[\w@.+-]+", q, flags=re.UNICODE))
                if not safe:
                    raise ValueError("empty")
                rows = list(
                    con.execute(
                        "SELECT p.* FROM vault_fts f "
                        "JOIN vault_profiles p ON p.id = f.rowid "
                        "WHERE vault_fts MATCH ? ORDER BY p.id DESC LIMIT ?",
                        (safe, limit * 3),
                    )
                )
            except sqlite3.OperationalError:
                like = f"%{q}%"
                rows = list(
                    con.execute(
                        "SELECT * FROM vault_profiles WHERE search_blob LIKE ? "
                        "ORDER BY id DESC LIMIT ?",
                        (like, limit * 3),
                    )
                )
        else:
            rows = list(con.execute("SELECT * FROM vault_profiles ORDER BY id DESC LIMIT ?", (limit * 3,)))
    finally:
        con.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        p = dict(row)
        age = get_age(p.get("dob"), p.get("age"))
        p["age"] = age
        if age is not None and age < 18:
            continue
        if min_age is not None and (age is None or age < min_age):
            continue
        if max_age is not None and (age is None or age > max_age):
            continue
        if not _exact_alias(p.get("gender"), gender, GENDER_ALIASES):
            continue
        if not _contains(p.get("name"), name):
            continue
        if not _contains(p.get("father_name"), father_name):
            continue
        if not _contains(p.get("mother_name"), mother_name):
            continue
        if not _exact_alias(p.get("nakshatram"), stars, STAR_ALIASES_VAULT):
            continue
        if not _exact_alias(p.get("padam"), padam, None):
            continue
        if not _exact_alias(p.get("rashi"), rashi, RASHI_ALIASES):
            continue
        if not _exact_alias(p.get("gotram"), gotram, GOTRAM_ALIASES):
            continue
        if not _exact_alias(p.get("saka"), saka, SAKA_ALIASES):
            continue
        if not _contains(p.get("birthplace"), birthplace) and not _exact_alias(
            p.get("birthplace"), birthplace, PLACE_ALIASES
        ):
            continue
        if not _contains(p.get("education"), education):
            continue
        if not _contains(p.get("location"), location):
            continue
        if not _contains(p.get("phone"), phone):
            continue
        out.append(p)
        if len(out) >= limit:
            break
    return out
