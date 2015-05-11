import os
import logging
import logging.handlers

import fss.config

_LOGGER = logging.getLogger()
_FORCE_LOG = bool(int(os.environ.get('FSS_DEBUG_LOG', '0')))
IS_DEBUG_LOG = fss.config.IS_DEBUG or _FORCE_LOG

DEFAULT_FORMAT_STRING = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

if IS_DEBUG_LOG is True:
    _LOGGER.setLevel(logging.DEBUG)
else:
    _LOGGER.setLevel(logging.WARNING)

def configure_handler(logger, h):
    formatter = logging.Formatter(DEFAULT_FORMAT_STRING)
    h.setFormatter(formatter)
    logger.addHandler(h)

def add_console_handler(logger):
    sh = logging.StreamHandler()
    configure_handler(logger, sh)

add_console_handler(_LOGGER)
