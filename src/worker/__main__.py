"""CLI: python -m src.worker"""

from __future__ import annotations

import logging

from src.env import load_env

load_env()

import time

from src.jobs.database import init_db
from src.worker.config import WorkerConfig
from src.worker.runner import run_once

logger = logging.getLogger("src.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db()
    config = WorkerConfig.from_env()
    logger.info("Worker démarré (poll toutes les %ss). Ctrl+C pour arrêter.", config.poll_interval)

    while True:
        try:
            worked = run_once(config)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            # Une base injoignable ne doit pas tuer le worker : on réessaie au tour suivant.
            logger.error("Erreur pendant le tour de boucle : %s", exc)
            worked = False

        if not worked:
            try:
                time.sleep(config.poll_interval)
            except KeyboardInterrupt:
                break

    logger.info("Worker arrêté.")


if __name__ == "__main__":
    main()
