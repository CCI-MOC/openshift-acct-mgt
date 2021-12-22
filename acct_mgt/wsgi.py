"""WSGI wrapper for tooling that expects a top-level application object"""

import logging

from . import app

APP = app.create_app()

if __name__ == "__main__":
    APP.run()
else:
    APP.logger = logging.getLogger("gunicorn.error")
    # logger level INFO = 20 see (https://docs.python.org/3/library/logging.html#levels)
    APP.logger.setLevel(20)
