"""Scan vault_inbox/ and load profiles into the local Vault DB."""
from __future__ import annotations

import re
from pathlib import Path

from vault.db import upsert_profile
from vault.extract import SUPPORTED_SUFFIXES, extract_text
from vault.parser import parse_vault_profile

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INBOX = ROOT / "vault_inbox"
_CONSENT_RE = re.compile(r"(?:^|\n)\s*(?:/submit(?:@\w+)?\s+)?CONSENT\s*:\s*YES\b", re.I)
_UNSAFE_NAME = re.compile(r"[^\w.\- ()]+", re.UNICODE)


def split_blocks(text: str) -> list[str]:
    if _CONSENT_RE.search(text):
        parts = re.split(
            r"(?=(?:^|\n)\s*(?:/submit(?:@\w+)?\s+)?CONSENT\s*:\s*YES\b)",
            text,
            flags=re.I,
        )
        return [p.strip() for p in parts if p.strip()]
    return [b.strip() for b in re.split(r"\n\s*\n+", text) if b.strip()]


def ingest_text(text: str, *, source_file: str, source_kind: str,
                require_consent_tag: bool = False) -> tuple[int, int]:
    accepted = skipped = 0
    for block in split_blocks(text):
        if require_consent_tag and not _CONSENT_RE.search(block):
            skipped += 1
            continue
        profile = parse_vault_profile(block)
        if not profile:
            skipped += 1
            continue
        age = profile.get("age")
        if age is not None and age < 18:
            skipped += 1
            continue
        upsert_profile(profile, source_file=source_file, source_kind=source_kind)
        accepted += 1
    return accepted, skipped


def _empty_stats() -> dict:
    return {"files": 0, "accepted": 0, "skipped": 0, "errors": 0, "unsupported": 0, "notes": []}


def _note(stats: dict, text: str) -> None:
    if text and len(stats["notes"]) < 4:
        stats["notes"].append(text[:200])


def safe_upload_name(name: str) -> str:
    """Keep only the file's own name, with characters that are safe on Windows and Linux."""
    base = Path(str(name or "").replace("\x00", "")).name
    base = _UNSAFE_NAME.sub("_", base).strip(" .")
    if not base or base in {".", ".."}:
        return "upload.txt"
    return base[:180]


def _ingest_file(
    path: Path,
    *,
    source_file: str,
    require_consent_tag: bool,
    stats: dict,
    allow_blank_suffix: bool,
) -> None:
    suffix = path.suffix.casefold()
    if suffix == "" and allow_blank_suffix:
        pass
    elif suffix not in SUPPORTED_SUFFIXES:
        stats["unsupported"] += 1
        _note(stats, f"{path.name}: this file type is not read")
        return
    try:
        text, kind = extract_text(path)
        if not text.strip():
            stats["skipped"] += 1
            stats["files"] += 1
            _note(stats, f"{path.name}: no text found")
            return
        yes, no = ingest_text(
            text,
            source_file=source_file,
            source_kind=kind,
            require_consent_tag=require_consent_tag,
        )
        stats["accepted"] += yes
        stats["skipped"] += no
        stats["files"] += 1
    except Exception as exc:
        stats["errors"] += 1
        detail = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        _note(stats, f"{path.name}: {detail}")


def ingest_inbox(
    inbox: Path | None = None,
    *,
    permission_confirmed: bool = False,
    require_consent_tag: bool = False,
) -> dict:
    if not permission_confirmed:
        raise ValueError("Confirm permission before importing personal biodata into the Vault.")
    inbox = Path(inbox or DEFAULT_INBOX)
    if not inbox.is_dir():
        raise FileNotFoundError(f"Inbox not found: {inbox}")

    stats = _empty_stats()
    skip_names = {"PUT_FILES_HERE.txt", ".gitkeep"}
    for path in sorted(inbox.rglob("*")):
        if not path.is_file() or path.name in skip_names or path.name.startswith("."):
            continue
        rel = str(path.relative_to(inbox))
        _ingest_file(
            path,
            source_file=rel,
            require_consent_tag=require_consent_tag,
            stats=stats,
            allow_blank_suffix=True,
        )
    return stats


def ingest_uploaded(
    files: list[tuple[str, bytes | str]],
    *,
    permission_confirmed: bool = False,
    require_consent_tag: bool = False,
    dest_dir: Path | None = None,
) -> dict:
    """Save files chosen on this computer, then read the ones Vault understands."""
    if not permission_confirmed:
        raise ValueError("Confirm permission before importing personal biodata into the Vault.")
    dest = Path(dest_dir or (DEFAULT_INBOX / "uploads")).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    stats = _empty_stats()
    used: set[str] = set()
    for raw_name, raw_data in files:
        name = safe_upload_name(raw_name)
        stem, suffix = Path(name).stem, Path(name).suffix
        candidate = name
        n = 2
        while candidate.casefold() in used:
            candidate = f"{stem}_{n}{suffix}"
            n += 1
        used.add(candidate.casefold())
        suffix_cf = Path(candidate).suffix.casefold()
        if suffix_cf not in SUPPORTED_SUFFIXES:
            stats["unsupported"] += 1
            _note(stats, f"{candidate}: this file type is not read")
            continue
        path = (dest / candidate).resolve()
        if not path.is_relative_to(dest):
            stats["errors"] += 1
            _note(stats, f"{candidate}: unsafe file name")
            continue
        data = raw_data.encode("utf-8") if isinstance(raw_data, str) else raw_data
        path.write_bytes(data)
        _ingest_file(
            path,
            source_file=candidate,
            require_consent_tag=require_consent_tag,
            stats=stats,
            allow_blank_suffix=False,
        )
    return stats
