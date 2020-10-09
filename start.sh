#!/bin/bash
cd /app
gunicorn -b 0.0.0.0:8080 -c /app/config.py -e PYTHONBUFFERED=TRUE wsgi:APP --log-file=-

