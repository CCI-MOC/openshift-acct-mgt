""" this is just sets things up to runing flask by gunicorn in a container """
# Disabling the pylint message about the 'forward_allowed_ips' even
# though this is a constanst it is for gunicorn.
# pylint: disable=C0103
import os

workers = int(os.environ.get("GUNICORN_PROCESSES", "3"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))

forwarded_allow_ips = "*"
secure_scheme_headers = {"X-Forwarded-Proto": "https"}
