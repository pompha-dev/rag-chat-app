import logging
import logging.config
import os

def setup_logging():
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "app.log")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            },
            "json": {
                "format": (
                    '{"time": "%(asctime)s", '
                    '"level": "%(levelname)s", '
                    '"logger": "%(name)s", '
                    '"message": "%(message)s"}'
                ),
            },
        },

        "handlers": {
            # Console (stdout) — important for Docker/Kubernetes
            "console": {
                "class": "logging.StreamHandler",
                "level": LOG_LEVEL,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },

            # Rotating file handler (prevents huge log files)
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": LOG_LEVEL,
                "formatter": "standard",
                "filename": LOG_FILE,
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },

        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
        },
    }

    logging.config.dictConfig(logging_config)