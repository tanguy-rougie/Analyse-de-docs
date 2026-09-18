"""Réglages du worker depuis l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


@dataclass(frozen=True)
class WorkerConfig:
    """Configuration de la boucle du worker."""

    poll_interval: float
    simulated_duration: float

    @classmethod
    def from_env(cls) -> WorkerConfig:
        return cls(
            poll_interval=_env_float("WORKER_POLL_INTERVAL", 2.0),
            simulated_duration=_env_float("WORKER_SIMULATED_DURATION", 3.0),
        )
