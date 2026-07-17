from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ordinary tests must be deterministic and must never contact an external model.
os.environ["GROQ_API_KEY"] = ""
os.environ["BLOCKCHAIN_ENABLED"] = "false"
