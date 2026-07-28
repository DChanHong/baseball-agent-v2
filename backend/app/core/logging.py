import logging.config
from typing import Any

from app.core.config import get_settings


def configure_logging() -> None:
    """애플리케이션 표준 logging 설정을 적용합니다."""

    settings = get_settings()
    log_level = "DEBUG" if settings.app_debug else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "loggers": _build_loggers(log_level),
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
        }
    )


def _build_loggers(log_level: str) -> dict[str, dict[str, Any]]:
    return {
        "app": {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console"],
            "level": "INFO" if log_level == "DEBUG" else "WARNING",
            "propagate": False,
        },
    }
