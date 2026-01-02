import logging
from logging.handlers import RotatingFileHandler
import sys
import updater

logger = logging.getLogger(__name__)

def main() -> None:
    updater.run_upstream_script()


if __name__ == "__main__":
    handler = RotatingFileHandler('app.log', maxBytes=5*1024*1024, backupCount=5)

    logging.basicConfig(
        handlers=[handler,
                  logging.StreamHandler(sys.stdout)
                  ],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    try:
        main()
    except Exception:
        logger.exception('Critical Error: The program crashed unexpectedly')
        raise
