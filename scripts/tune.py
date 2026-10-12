"""Alias ke skrip scripts/tune_weights.py untuk grid search bobot field."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.tune_weights import main

if __name__ == "__main__":
    main()
