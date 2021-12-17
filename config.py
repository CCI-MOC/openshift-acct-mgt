""" This is a config files used by gunicorn """
# Disabling the pylint message about the 'forward_allowed_ips' even
# as this is a constanst defined by gunicorn.
# pylint: disable=invalid-name
import os

workers = int(os.environ.get("GUNICORN_PROCESSES", "3"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))

forwarded_allow_ips = "*"
secure_scheme_headers = {"X-Forwarded-Proto": "https"}
