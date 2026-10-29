"""Readable profile formatting for Telegram and the desktop Vault."""
from __future__ import annotations

from datetime import date
from typing import Any


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
    star = _val(profile.get("nakshatram"), title=True)
    padam = profile.get("padam")
    if padam not in (None, ""):
        if star == "—":
            return f"Padam {_val(padam)}"
        return f"{star}  ·  Padam {_val(padam)}"
    return star


# Sections keep biodata scannable on phone and desktop.
_SECTIONS: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...] = (
    (
        "Personal",
        (
            ("Gender", lambda p: _val(p.get("gender"), title=True)),
            ("Age / DOB", _age_dob_line),
            ("Birthplace", lambda p: _val(p.get("birthplace"), title=True)),
            ("Location", lambda p: _val(p.get("location"), title=True)),
        ),
    ),
    (
        "Family",
        (
            ("Father", lambda p: _val(p.get("father_name"))),
            ("Mother", lambda p: _val(p.get("mother_name"))),
            ("Gotram", lambda p: _val(p.get("gotram"), title=True)),
            ("Saka", lambda p: _val(p.get("saka"), title=True)),
        ),
    ),
    (
        "Astrology",
        (
            ("Nakshatram", _star_line),
            ("Rashi", lambda p: _val(p.get("rashi"), title=True)),
        ),
    ),
    (
        "Education",
        (("Education", lambda p: _val(p.get("education"))),),
    ),
)

_KEEP_ALWAYS = {
    "Gender",
    "Age / DOB",
    "Nakshatram",
    "Rashi",
    "Birthplace",
    "Education",
    "Phone",
}


def profile_rows(profile: dict, *, include_phone: bool = False) -> list[tuple[str, str]]:
    """Flat labeled rows (no section headers) for simple consumers/tests."""
    rows: list[tuple[str, str]] = []
    for _section, fields in _SECTIONS:
        for label, fn in fields:
            rows.append((label, fn(profile)))
    if include_phone:
        # Phone after family name fields, before astrology — natural contact spot.
        insert_at = next((i for i, (lab, _) in enumerate(rows) if lab == "Nakshatram"), len(rows))
        rows.insert(insert_at, ("Phone", _val(profile.get("phone"))))
    source = profile.get("source_name") or profile.get("source_file")
    if source:
        rows.append(("Source", _val(source)))
    cleaned: list[tuple[str, str]] = []
    for label, value in rows:
        if value == "—" and label not in _KEEP_ALWAYS:
            continue
        cleaned.append((label, value))
    return cleaned


def profile_sections(profile: dict, *, include_phone: bool = False) -> list[tuple[str, list[tuple[str, str]]]]:
    """Grouped biodata sections; empty optional rows omitted."""
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for section, fields in _SECTIONS:
        rows: list[tuple[str, str]] = []
        for label, fn in fields:
            value = fn(profile)
            if value == "—" and label not in _KEEP_ALWAYS:
                continue
            rows.append((label, value))
        if section == "Family" and include_phone:
            phone = _val(profile.get("phone"))
            if phone != "—" or "Phone" in _KEEP_ALWAYS:
                # Place phone after parents when present.
                insert = 0
                for i, (lab, _) in enumerate(rows):
                    if lab in ("Father", "Mother"):
                        insert = i + 1
                rows.insert(insert, ("Phone", phone))
        if rows:
            out.append((section, rows))
    source = profile.get("source_name") or profile.get("source_file")
    if source:
        out.append(("Source", [("File", _val(source))]))
    return out


def format_profile_text(profile: dict, *, index: int | None = None, include_phone: bool = False) -> str:
    """Comfortable plain-text biodata sheet for Telegram (mobile-friendly)."""
    name = _val(profile.get("name"))
    if name == "—":
        name = "Name unavailable"
    if index is not None:
        header = f"── {index}. {name} ──"
    else:
        header = f"── {name} ──"
    lines = [header, ""]
    for section, rows in profile_sections(profile, include_phone=include_phone):
        lines.append(section)
        for label, value in rows:
            lines.append(f"  {label}: {value}")
        lines.append("")
    return "\n".join(lines).rstrip()


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

    subtitle_bits: list[str] = []
    if profile.get("gender"):
        subtitle_bits.append(_val(profile.get("gender"), title=True))
    if profile.get("age") not in (None, ""):
        subtitle_bits.append(f"{profile.get('age')} yrs")
    star = _star_line(profile)
    if star != "—":
        subtitle_bits.append(star)
    if include_phone:
        phone = _val(profile.get("phone"))
        if phone != "—":
            subtitle_bits.append(phone)
    sub = " · ".join(subtitle_bits)

    sections_html: list[str] = []
    for section, rows in profile_sections(profile, include_phone=include_phone):
        row_bits = []
        for label, value in rows:
            row_bits.append(
                '<div class="mv-row">'
                f'<div class="mv-label">{_escape(label)}</div>'
                f'<div class="mv-value">{_escape(value)}</div>'
                "</div>"
            )
        sections_html.append(
            f'<div class="mv-section">'
            f'<div class="mv-section-title">{_escape(section)}</div>'
            f'{"".join(row_bits)}'
            f"</div>"
        )

    return (
        f'<article class="mv-sheet">'
        f'<header class="mv-header">'
        f'<div class="mv-name">{_escape(title)}</div>'
        f'<div class="mv-sub">{_escape(sub)}</div>'
        f"</header>"
        f'{"".join(sections_html)}'
        f"</article>"
    )


def vault_stylesheet() -> str:
    """Shared CSS injected once by the Vault Streamlit app."""
    return """
<style>
  .block-container { max-width: 760px; padding-top: 1.35rem; padding-bottom: 3rem; }
  h1 { letter-spacing: -0.02em; font-weight: 650; }
  .mv-sheet {
    background: linear-gradient(180deg, #fbfcfe 0%, #f4f7fa 100%);
    border: 1px solid #d5dee8;
    border-radius: 14px;
    padding: 1.15rem 1.35rem 0.85rem;
    margin: 0 0 1.15rem 0;
    box-shadow: 0 1px 0 rgba(20, 50, 74, 0.04);
  }
  .mv-header { margin-bottom: 0.85rem; padding-bottom: 0.75rem; border-bottom: 1px solid #e2eaf1; }
  .mv-name { font-size: 1.28rem; font-weight: 650; color: #14324a; line-height: 1.3; }
  .mv-sub { color: #5f7386; margin-top: 0.28rem; font-size: 0.95rem; line-height: 1.4; }
  .mv-section { margin: 0.55rem 0 0.85rem; }
  .mv-section-title {
    font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: #7a8b9a; font-weight: 650; margin: 0 0 0.35rem 0;
  }
  .mv-row {
    display: flex; gap: 1rem; align-items: baseline;
    padding: 0.38rem 0; border-bottom: 1px solid #eaf0f5;
  }
  .mv-row:last-child { border-bottom: none; }
  .mv-label { min-width: 7.2rem; color: #5b6b7c; font-size: 0.9rem; flex-shrink: 0; }
  .mv-value { flex: 1; color: #1c2a36; font-size: 1.05rem; line-height: 1.5; word-break: break-word; }
  @media (max-width: 640px) {
    .mv-row { flex-direction: column; gap: 0.15rem; }
    .mv-label { min-width: 0; }
  }
</style>
"""


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
    star = _val(profile.get("nakshatram"), title=True)
    return f"{index}. {name}\n    Star: {star}  ·  Source: {source}"
