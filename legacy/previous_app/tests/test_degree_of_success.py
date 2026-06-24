from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.degree_of_success import resolve_outcome


def test_nat20_shift_promotes_degree_by_one():
    # Bazowo failure (10 vs DC 15), po nat20 -> success.
    assert resolve_outcome(10, 15, natural_shift=1) == "success"


def test_nat1_shift_demotes_degree_by_one():
    # Bazowo success (10 vs DC 10), po nat1 -> failure.
    assert resolve_outcome(10, 10, natural_shift=-1) == "failure"
