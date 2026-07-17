from __future__ import annotations

import json
from pathlib import Path

from api.main import create_app


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app(enable_saas=True).openapi()
    target.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
