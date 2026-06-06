import sys
from pathlib import Path

_ALGORITHM_ROOT = Path(__file__).resolve().parent.parent / "algorithm"
if str(_ALGORITHM_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALGORITHM_ROOT))
