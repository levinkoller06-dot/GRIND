"""Kleiner Test, ob der OpenRouter-Key für Jev funktioniert.

Aufruf (im Ordner backend):  uv run python jev_test.py
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Egal wie gestartet (z. B. Run-Button in VS Code): immer mit dem Python aus
# backend/.venv und im Ordner backend laufen, damit Pakete und .env gefunden werden.
HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if VENV_PY.exists() and Path(sys.prefix).resolve() != (HERE / ".venv").resolve():
    sys.exit(subprocess.call([str(VENV_PY), __file__]))
os.chdir(HERE)
sys.path.insert(0, str(HERE))

from app import jev  # noqa: E402


async def main() -> None:
    answers = await jev.decide(
        state="Es ist 7 Uhr morgens, draußen regnet es stark und es sind 4 Grad.",
        questions={"jacke": jev.noul("Sollte man heute eine Regenjacke anziehen?")},
    )
    prozent = answers["jacke"]["noul"] * 100
    print(f"Key funktioniert! Jev sagt: {prozent:.0f} % Regenjacke anziehen.")


asyncio.run(main())
