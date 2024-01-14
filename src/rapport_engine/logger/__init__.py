import logging
import os
import structlog


def configure() -> None:
    debug_mode = os.environ.get("RAPPORT_DEBUG_MODE", "true").lower() in [
        "true",
        "1",
    ]

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    suppress_modules = ["httpx"]

    if debug_mode:
        logging.basicConfig(level=logging.DEBUG)
        processors.append(structlog.dev.ConsoleRenderer())

    else:
        logging.basicConfig(level=logging.INFO)
        suppress_modules.append("telegram")
        processors.append(structlog.processors.JSONRenderer())

    for module in suppress_modules:
        logging.getLogger(module).setLevel(logging.CRITICAL)

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get() -> any:
    return structlog.get_logger()
