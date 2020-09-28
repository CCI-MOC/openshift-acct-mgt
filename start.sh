#!/bin/bash
cd /app/openshift-acct-mgt
gunicorn -b 0.0.0.0:8080 -c /app/openshift-acct-mgt/config.py -e PYTHONBUFFERED=TRUE wsgi:application --log-file=-

