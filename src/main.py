from logging.handlers import RotatingFileHandler
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from typing import List, Optional
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope

import twitch

# Logging-related env vars
LOG_LEVEL = str(os.getenv("LOG_LEVEL", "INFO")).upper()
LOG_FILE = str(os.getenv("LOG_FILE", "log.log"))
log_format = "[%(levelname)s] [%(asctime)s] %(message)s"
logging.basicConfig(format=log_format, level=LOG_LEVEL, stream=sys.stdout)
LOGGER = logging.getLogger()
rotating_file_handler = RotatingFileHandler(
    filename=LOG_FILE,
    maxBytes=1048576*15,
    backupCount=3,
)
formatter = logging.Formatter(log_format)
rotating_file_handler.setFormatter(formatter)
rotating_file_handler.setLevel(LOG_LEVEL)
LOGGER.addHandler(rotating_file_handler)

if __name__ == '__main__':
    asyncio.run(twitch.run())
