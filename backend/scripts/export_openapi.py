"""Export the OpenAPI schema to docs/openapi.json (CI / docs artifact)."""
from __future__ import annotations

import json
import pathlib
import sys

# Allow running as `python scripts/export_openapi.py` from the backend dir.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def main() -> None:
    out = pathlib.Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(app.openapi(), indent=2))
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
