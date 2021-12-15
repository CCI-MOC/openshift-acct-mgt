#!/bin/bash
exec gunicorn -b 0.0.0.0:8080 -c config.py -e PYTHONBUFFERED=TRUE wsgi:APP --log-file=-

