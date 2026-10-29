"""Launch the local Matrimony Vault UI.

Works on Windows even when `streamlit` is not on PATH:

    python run_vault.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "vault" / "app.py"


def main() -> None:
    # Use `python -m streamlit` so Scripts/ does not need to be on PATH (common on Windows).
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "streamlit", "run", str(APP)])
    )


if __name__ == "__main__":
    main()
