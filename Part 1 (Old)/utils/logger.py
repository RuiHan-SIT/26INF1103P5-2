import logging

# Configure logger
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("handover_logger")