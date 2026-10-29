"""Import exports from the local resources/ folder into the profile database.

Usage:
  python import_resources.py --i-have-permission
  python import_resources.py --i-have-permission --dir resources
  python import_resources.py --i-have-permission --allow-labeled-without-consent-tag

Put Telegram/WhatsApp text exports and Telegram JSON under resources/.
Images and PDFs are skipped (no OCR yet). Only import people you may process.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core import import_resources_dir

ROOT = Path(__file__).resolve().parent
DEFAULT_DIR = ROOT / "resources"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import consented/labeled profiles from resources/")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help="Folder containing exports (default: ./resources)",
    )
    parser.add_argument(
        "--i-have-permission",
        action="store_true",
        help="Confirm you have permission to process people in these exports",
    )
    parser.add_argument(
        "--allow-labeled-without-consent-tag",
        action="store_true",
        help="Also import labeled biodata blocks that lack the literal CONSENT:YES line "
             "(still requires --i-have-permission). Prefer tagging CONSENT:YES when possible.",
    )
    args = parser.parse_args()
    if not args.i_have_permission:
        parser.error("You must confirm permission with --i-have-permission")
    stats = import_resources_dir(
        args.dir,
        permission_confirmed=True,
        require_consent_tag=not args.allow_labeled_without_consent_tag,
    )
    print(
        f"Scanned {args.dir}: {stats['files']} text/json file(s), "
        f"{stats['accepted']} profile(s) imported, {stats['skipped']} block(s) skipped, "
        f"{stats['ignored_media']} media/other file(s) ignored."
    )
    print("Next: set bot filters (/setstar, /setage, …) then /matches or open the dashboard.")


if __name__ == "__main__":
    main()
