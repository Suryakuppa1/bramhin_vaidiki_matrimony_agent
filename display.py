"""Readable profile formatting for Telegram and the desktop Vault."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable


def _val(value: Any, *, title: bool = False) -> str:
    if value is None or str(value).strip() == "":
        return "—"
    text = str(value).strip()
    if "_" in text:
        text = text.replace("_", " ")
    if title and text == text.casefold():
        text = text.title()
    return text


def _pretty_dob(dob: Any) -> str:
    if not dob:
        return "—"
    try:
        return date.fromisoformat(str(dob)).strftime("%d %b %Y")
    except ValueError:
        return _val(dob)


def _age_dob_line(profile: dict) -> str:
    age = profile.get("age")
    dob = _pretty_dob(profile.get("dob"))
    if age not in (None, "") and dob != "—":
        return f"{age} yrs  ·  {dob}"
    if age not in (None, ""):
        return f"{age} yrs"
    return dob


def _star_line(profile: dict) -> str:
    star = _val(profile.get("nakshatram"))
    padam = profile.get("padam")
    if padam not in (None, ""):
        if star == "—":
            return f"Padam {_val(padam)}"
        return f"{star}  ·  Padam {_val(padam)}"
    return star


# (label, value-builder) — phone optional for Telegram bot privacy.
_BASE_ROWS = (
    ("Gender", lambda p: _val(p.get("gender"))),
    ("Age / DOB", _age_dob_line),
    ("Father", lambda p: _val(p.get("father_name"))),
    ("Mother", lambda p: _val(p.get("mother_name"))),
    ("Nakshatram", _star_line),
    ("Rashi", lambda p: _val(p.get("rashi"))),
    ("Gotram", lambda p: _val(p.get("gotram"))),
    ("Saka", lambda p: _val(p.get("saka"))),
    ("Birthplace", lambda p: _val(p.get("birthplace"))),
    ("Education", lambda p: _val(p.get("education"))),
    ("Location", lambda p: _val(p.get("location"))),
)


def profile_rows(profile: dict, *, include_phone: bool = False) -> list[tuple[str, str]]:
    rows = [(label, fn(profile)) for label, fn in _BASE_ROWS]
    if include_phone:
        rows.insert(4, ("Phone", _val(profile.get("phone"))))
    source = profile.get("source_name") or profile.get("source_file")
    if source:
        rows.append(("Source", _val(source)))
    # Drop empty optional rows that are all dashes except keep core identity lines
    keep_always = {"Gender", "Age / DOB", "Nakshatram", "Rashi", "Birthplace", "Education", "Phone"}
    cleaned = []
    for label, value in rows:
        if value == "—" and label not in keep_always:
            continue
        cleaned.append((label, value))
    return cleaned


def format_profile_text(profile: dict, *, index: int | None = None, include_phone: bool = False) -> str:
    """Comfortable plain-text biodata block (Telegram-friendly)."""
    name = _val(profile.get("name"))
    if name == "—":
        name = "Name unavailable"
    title = f"{index}. {name}" if index is not None else name
    rule = "—" * 28
    lines = [rule, title, rule]
    for label, value in profile_rows(profile, include_phone=include_phone):
        lines.append(f"{label:<12} {value}")
    return "\n".join(lines)


def format_matches_list(
    profiles: list[dict],
    *,
    header: str,
    include_phone: bool = False,
    limit: int = 8,
) -> list[str]:
    """Return one or more Telegram messages under the 4096-char limit."""
    if not profiles:
        return [header]
    chunks: list[str] = []
    current = header.strip() + "\n"
    shown = profiles[:limit]
    for i, profile in enumerate(shown, 1):
        block = "\n" + format_profile_text(profile, index=i, include_phone=include_phone) + "\n"
        if len(current) + len(block) > 3500 and current.strip() != header.strip():
            chunks.append(current.rstrip())
            current = block.lstrip("\n")
        else:
            current += block
    if len(profiles) > limit:
        current += f"\n… and {len(profiles) - limit} more. Use /export excel for the full list.\n"
    chunks.append(current.rstrip())
    return chunks


def format_profile_html(profile: dict, *, index: int | None = None, include_phone: bool = True) -> str:
    """Readable HTML biodata sheet for the desktop Vault."""
    name = _val(profile.get("name"))
    if name == "—":
        name = "Name unavailable"
    title = f"{index}. {name}" if index is not None else name
    rows_html = []
    for label, value in profile_rows(profile, include_phone=include_phone):
        rows_html.append(
            f'<div style="display:flex; gap:1rem; padding:0.45rem 0; border-bottom:1px solid #e8eef3;">'
            f'<div style="min-width:7.5rem; color:#5b6b7c; font-size:0.92rem;">{label}</div>'
            f'<div style="flex:1; color:#1c2a36; font-size:1.02rem; line-height:1.45;">{_escape(value)}</div>'
            f"</div>"
        )
    phone = _val(profile.get("phone")) if include_phone else ""
    subtitle = []
    if profile.get("gender"):
        subtitle.append(_val(profile.get("gender")).title())
    if profile.get("age") not in (None, ""):
        subtitle.append(f"{profile.get('age')} yrs")
    if include_phone and phone != "—":
        subtitle.append(phone)
    sub = " · ".join(subtitle)
    return (
        f'<div style="background:#f7fafc; border:1px solid #d9e3ec; border-radius:12px; '
        f'padding:1.1rem 1.25rem; margin:0 0 1rem 0;">'
        f'<div style="font-size:1.25rem; font-weight:650; color:#14324a; margin-bottom:0.2rem;">{_escape(title)}</div>'
        f'<div style="color:#607487; margin-bottom:0.75rem; font-size:0.95rem;">{_escape(sub)}</div>'
        f'{"".join(rows_html)}'
        f"</div>"
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_review_line(profile: dict, *, index: int) -> str:
    name = _val(profile.get("name"))
    source = _val(profile.get("source_name") or profile.get("source_file"))
    star = _val(profile.get("nakshatram"))
    return f"{index}. {name}\n    Star: {star}  ·  Source: {source}"
