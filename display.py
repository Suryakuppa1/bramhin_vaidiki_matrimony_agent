"""Readable profile formatting for Telegram and the desktop Vault."""
from __future__ import annotations

import base64
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

_BACKGROUND = Path(__file__).resolve().parent / "assets" / "wedding_background.jpg"


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


def format_vault_report(profiles: list[dict], *, summary: str) -> str:
    """Plain biodata sheets for a downloaded text copy of a Submit result."""
    lines = [
        "Wedding Vault",
        summary or "All stored profiles",
        f"Profiles: {len(profiles)}",
        "",
    ]
    if not profiles:
        lines.append("No profiles matched these fields.")
        return "\n".join(lines).rstrip() + "\n"
    blocks = [
        format_profile_text(profile, index=index, include_phone=True)
        for index, profile in enumerate(profiles, 1)
    ]
    return "\n\n".join(lines + blocks).rstrip() + "\n"


def vault_hero_html(profile_count: int) -> str:
    noun = "profile" if profile_count == 1 else "profiles"
    return (
        '<div class="mv-hero">'
        '<div class="mv-kicker">A private desk for family matching</div>'
        '<div class="mv-hero-title">Wedding Vault</div>'
        '<p class="mv-hero-lead">Choose the fields you need from the menus, then press Submit. '
        "Each profile comes back as a biodata sheet.</p>"
        f'<div class="mv-count">{profile_count} {noun} stored on this computer</div>'
        "</div>"
    )


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


@lru_cache(maxsize=1)
def _background_image_url() -> str:
    if not _BACKGROUND.is_file():
        return ""
    encoded = base64.b64encode(_BACKGROUND.read_bytes()).decode("ascii")
    return f'url("data:image/jpeg;base64,{encoded}")'


def vault_stylesheet() -> str:
    """Shared CSS injected once by the Vault Streamlit app."""
    photo = _background_image_url()
    if photo:
        background = (
            "linear-gradient(180deg, rgba(255,248,242,0.2), rgba(255,244,236,0.34)), " + photo
        )
    else:
        background = "linear-gradient(165deg, #fff9f4 0%, #f7e7ea 46%, #f3e6d4 100%)"
    return """
<style>
  .stApp, [data-testid="stAppViewContainer"] {
    background-color: #f3e6d4 !important;
    background-image: __BG__ !important;
    background-size: cover !important;
    background-position: center top !important;
    background-attachment: fixed !important;
    background-repeat: no-repeat !important;
    color: #3b241c;
  }
  header[data-testid="stHeader"] { background: transparent !important; }
  section.main > div { background: transparent !important; }
  .block-container {
    max-width: 980px !important;
    margin-top: 3.2rem;
    padding-top: 1.35rem !important;
    padding-bottom: 2.6rem;
    background: rgba(255, 250, 246, 0.9);
    border: 1px solid rgba(196, 163, 106, 0.72);
    border-radius: 28px;
    box-shadow: 0 24px 60px rgba(110, 36, 54, 0.12);
  }
  .mv-hero { text-align: center; margin: 0.2rem 0 1.15rem; }
  .mv-kicker {
    letter-spacing: 0.16em; text-transform: uppercase; font-size: 0.74rem;
    color: #a06a3a; font-weight: 650;
  }
  .mv-hero-title {
    font-family: Georgia, "Palatino Linotype", Palatino, serif;
    font-size: 2.7rem; line-height: 1.1; color: #6e2436; font-weight: 600;
    margin: 0.25rem 0 0.4rem;
  }
  .mv-hero-lead {
    color: #5c463c; font-size: 1.02rem; line-height: 1.5; margin: 0 auto;
    max-width: 38rem;
  }
  .mv-count {
    display: inline-block; margin-top: 0.75rem; padding: 0.28rem 0.8rem;
    border-radius: 999px; border: 1px solid #e4d0b0; background: rgba(255, 248, 242, 0.85);
    color: #6e2436; font-size: 0.88rem;
  }
  .mv-panel-title {
    font-family: Georgia, "Palatino Linotype", Palatino, serif;
    color: #6e2436; font-size: 1.45rem; margin: 0.2rem 0 0.25rem;
  }
  .mv-waiting {
    margin: 0.4rem 0 0.2rem; padding: 0.9rem 1rem; text-align: center;
    border: 1px dashed #e4d0b0; border-radius: 16px; color: #6b5348;
    background: rgba(255, 248, 242, 0.65);
  }
  .mv-sheet {
    background: linear-gradient(180deg, #fffdfb 0%, #fff6f2 100%);
    border: 1px solid #e4d0b0;
    border-radius: 18px;
    padding: 1.15rem 1.35rem 0.85rem;
    margin: 0 0 1.15rem 0;
    box-shadow: 0 10px 28px rgba(122, 49, 66, 0.06);
  }
  .mv-header { margin-bottom: 0.85rem; padding-bottom: 0.75rem; border-bottom: 1px solid #f0e2d2; }
  .mv-name {
    font-family: Georgia, "Palatino Linotype", Palatino, serif;
    font-size: 1.35rem; font-weight: 650; color: #6e2436; line-height: 1.3;
  }
  .mv-sub { color: #7a5b4a; margin-top: 0.28rem; font-size: 0.95rem; line-height: 1.4; }
  .mv-section { margin: 0.55rem 0 0.85rem; }
  .mv-section-title {
    font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: #a06a3a; font-weight: 650; margin: 0 0 0.35rem 0;
  }
  .mv-row {
    display: flex; gap: 1rem; align-items: baseline;
    padding: 0.38rem 0; border-bottom: 1px solid #f3e8df;
  }
  .mv-row:last-child { border-bottom: none; }
  .mv-label { min-width: 7.2rem; color: #7a5b4a; font-size: 0.9rem; flex-shrink: 0; }
  .mv-value { flex: 1; color: #3b241c; font-size: 1.05rem; line-height: 1.5; word-break: break-word; }
  .stApp [data-testid="stBaseButton-primary"],
  .stApp [data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(180deg, #a24b5c 0%, #7c3142 100%) !important;
    color: #fffaf6 !important;
    border: 1px solid #e7d3a1 !important;
    border-radius: 999px !important;
    font-weight: 650;
    letter-spacing: 0.03em;
  }
  .stApp [data-testid="stBaseButton-secondary"],
  .stApp [data-testid="stBaseButton-secondaryFormSubmit"] {
    border-radius: 999px !important;
    border: 1px solid #c4a36a !important;
    background: #fffaf6 !important;
    color: #6e3140 !important;
    font-weight: 600;
  }
  .stApp button:disabled {
    opacity: 0.45 !important;
    cursor: not-allowed;
  }
  [data-testid="stFileUploader"] section {
    background: rgba(255, 250, 245, 0.72);
    border: 1px dashed #c4a36a;
    border-radius: 16px;
  }
  [data-testid="stForm"] {
    border: 1px solid rgba(228, 208, 176, 0.95);
    border-radius: 18px;
    background: rgba(255, 252, 248, 0.72);
    padding: 0.35rem 0.85rem 0.9rem;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 252, 248, 0.78);
    border-color: rgba(228, 208, 176, 0.95) !important;
    border-radius: 18px;
  }
  @media (max-width: 640px) {
    .block-container { margin-top: 1rem; border-radius: 18px; }
    .mv-hero-title { font-size: 2.1rem; }
    .mv-row { flex-direction: column; gap: 0.15rem; }
    .mv-label { min-width: 0; }
  }
</style>
""".replace("__BG__", background)


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
