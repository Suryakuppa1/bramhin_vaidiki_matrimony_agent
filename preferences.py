"""Private search preferences for authorized Telegram users.

No Telegram message contents, phone numbers or contact details are stored here.
"""
from __future__ import annotations

import json
from datetime import date
from core import connect, is_match, get_age

EMPTY = {"min_age": None, "max_age": None, "stars": "", "birthplace": "", "rashi": "", "education": "", "dob_start": None, "dob_end": None, "group": ""}


def read_filters(user_id: int | str) -> dict:
    con = connect()
    try:
        con.execute("CREATE TABLE IF NOT EXISTS user_filters (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        row = con.execute("SELECT data FROM user_filters WHERE user_id=?", (str(user_id),)).fetchone()
        if not row:
            return dict(EMPTY)
        return {**EMPTY, **json.loads(row['data'])}
    finally:
        con.close()


def save_filters(user_id: int | str, filters: dict) -> None:
    con = connect()
    try:
        con.execute("CREATE TABLE IF NOT EXISTS user_filters (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        con.execute("INSERT INTO user_filters(user_id, data) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data",
                    (str(user_id), json.dumps({k: filters.get(k) for k in EMPTY})))
        con.commit()
    finally:
        con.close()


def clear_filters(user_id: int | str) -> None:
    con = connect()
    try:
        con.execute("DELETE FROM user_filters WHERE user_id=?", (str(user_id),))
        con.commit()
    finally:
        con.close()


def configured(filters: dict) -> bool:
    return any(v is not None and str(v).strip() != '' for v in filters.values())


def criteria(filters: dict) -> dict:
    return {k: v for k, v in {**filters, "dob_start": date.fromisoformat(filters['dob_start']) if filters.get('dob_start') else None,
            "dob_end": date.fromisoformat(filters['dob_end']) if filters.get('dob_end') else None}.items() if k != 'group'}


def matching_rows(profiles: list[dict], filters: dict, *, include_review: bool = False, limit: int = 100) -> list[dict]:
    if not configured(filters):
        return []
    result = []
    for p in profiles:
        if p.get('duplicate_of'):
            continue
        if filters.get('group') and filters['group'].casefold() not in (p.get('source_name') or '').casefold():
            continue
        age = get_age(p.get('dob'), p.get('age'))
        if age is not None and age < 18:
            continue
        status = is_match(p, **criteria(filters))
        if status == 'Match' or (status == 'Needs review' and include_review):
            q = dict(p)
            q['age'] = age
            q['status'] = status
            result.append(q)
    result.sort(key=lambda x: (x['status'] != 'Match', x.get('name') or '', x.get('source_name') or ''))
    return result[:limit]


def describe_filters(f: dict) -> str:
    parts = []
    if f.get('min_age') is not None or f.get('max_age') is not None:
        parts.append(f"Age: {f.get('min_age') or 'any'}–{f.get('max_age') or 'any'}")
    for k, display in [('stars', 'Nakshatram'), ('birthplace', 'Birthplace'), ('rashi', 'Rashi'), ('education', 'Education'), ('group', 'Source group')]:
        if f.get(k):
            parts.append(f"{display}: {f[k]}")
    if f.get('dob_start') or f.get('dob_end'):
        parts.append(f"DOB: {f.get('dob_start') or 'any'} to {f.get('dob_end') or 'any'}")
    return '; '.join(parts) if parts else 'No requirements configured'
