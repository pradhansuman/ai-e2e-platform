import sys
from pathlib import Path

# Make both the backend package and the benchmark package importable, regardless
# of whether pytest is run from the repo root (`pytest tests`) or from backend/
# (`cd backend && python -m pytest ../tests`, which CI uses).
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))  # `app.*`
sys.path.insert(0, str(ROOT))     # `benchmark.*` (lives at repo root)
