"""CLI: python -m src.web"""

from __future__ import annotations

import os

import uvicorn

from src.env import load_env

load_env()


def main() -> None:
    host = os.environ.get("WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = int(os.environ.get("WEB_PORT", "8000"))
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
