# src/logger.py
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = os.getenv("GATEWAY_LOG", "gateway.log")

logger = logging.getLogger("gateway")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
# also console
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
