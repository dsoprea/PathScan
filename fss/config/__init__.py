import os

IS_DEBUG = bool(int(os.environ.get('FSS_DEBUG', '0')))
