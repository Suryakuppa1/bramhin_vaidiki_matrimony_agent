"""Launch the local Matrimony Vault UI: python run_vault.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "vault" / "app.py"


def main() -> None:
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(APP), "--server.headless=true"]))


if __name__ == "__main__":
    main()
