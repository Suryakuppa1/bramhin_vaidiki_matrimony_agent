"""Import consent-tagged history: python import_history.py file.json --i-have-permission"""
import argparse
from pathlib import Path
from core import import_export_json

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", type=Path, help="Telegram Desktop JSON exports")
    p.add_argument("--i-have-permission", action="store_true", help="Confirm permission to process the people in these exports")
    args = p.parse_args()
    if not args.i_have_permission:
        p.error("You must confirm appropriate permission with --i-have-permission")
    for f in args.files:
        yes, other = import_export_json(f.read_bytes(), filename=f.name, permission_confirmed=True)
        print(f"{f.name}: {yes} explicitly consent-tagged profiles imported, {other} other posts skipped")
