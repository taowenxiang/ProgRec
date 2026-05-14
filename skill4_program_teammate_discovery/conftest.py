"""Pytest: put package root on sys.path for `from skill...` imports."""

from __future__ import annotations

import sys
from pathlib import Path

_PTD_ROOT = Path(__file__).resolve().parent
if str(_PTD_ROOT) not in sys.path:
    sys.path.insert(0, str(_PTD_ROOT))
