import sys
from pathlib import Path

# Make the backend package importable when running pytest from the repo root.
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
