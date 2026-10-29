"""Scan vault_inbox/ and load profiles into the local Vault DB."""
from __future__ import annotations

import re
from pathlib import Path

from vault.db import upsert_profile
from vault.extract import (
    EXCEL_SUFFIXES, IMAGE_SUFFIXES, JSON_SUFFIXES, PDF_SUFFIXES, TEXT_SUFFIXES, extract_text,
)
from vault.parser import parse_vault_profile

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INBOX = ROOT / "vault_inbox"
_CONSENT_RE = re.compile(r"(?:^|\n)\s*(?:/submit(?:@\w+)?\s+)?CONSENT\s*:\s*YES\b", re.I)


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


def ingest_inbox(
    inbox: Path | None = None,
    *,
    permission_confirmed: bool = False,
    require_consent_tag: bool = False,
) -> dict[str, int]:
    if not permission_confirmed:
        raise ValueError("Confirm permission before importing personal biodata into the Vault.")
    inbox = Path(inbox or DEFAULT_INBOX)
    if not inbox.is_dir():
        raise FileNotFoundError(f"Inbox not found: {inbox}")

    stats = {"files": 0, "accepted": 0, "skipped": 0, "errors": 0, "unsupported": 0}
    skip_names = {"PUT_FILES_HERE.txt", ".gitkeep"}
    for path in sorted(inbox.rglob("*")):
        if not path.is_file() or path.name in skip_names or path.name.startswith("."):
            continue
        suffix = path.suffix.casefold()
        supported = suffix in TEXT_SUFFIXES | EXCEL_SUFFIXES | PDF_SUFFIXES | IMAGE_SUFFIXES | JSON_SUFFIXES | {""}
        if not supported:
            stats["unsupported"] += 1
            continue
        rel = str(path.relative_to(inbox))
        try:
            text, kind = extract_text(path)
            if not text.strip():
                stats["skipped"] += 1
                stats["files"] += 1
                continue
            yes, no = ingest_text(
                text,
                source_file=rel,
                source_kind=kind,
                require_consent_tag=require_consent_tag,
            )
            stats["accepted"] += yes
            stats["skipped"] += no
            stats["files"] += 1
        except Exception:
            stats["errors"] += 1
    return stats
