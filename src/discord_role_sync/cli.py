from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

from .config import ConfigError, load_config
from .discord_app import DiscordRoleSyncError, run


def _logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
        force=True,
    )
    logging.Formatter.converter = __import__("time").gmtime
    return logging.getLogger("discord-role-sync")


def main() -> int:
    load_dotenv()
    logger = _logger()
    try:
        config = load_config()
        summary = run(config, logger)
        return summary.exit_code
    except ConfigError as exc:
        logger.error("CONFIG_ERROR %s", exc)
        return 2
    except DiscordRoleSyncError as exc:
        logger.error("RUNTIME_ERROR %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
