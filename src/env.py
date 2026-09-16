"""Load .env from the repository root when present."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Populate os.environ from `.env` at repo root (no-op if missing or dotenv absent)."""
    env_file = _REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_file, override=False)
