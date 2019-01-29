gunicorn -b 0.0.0.0:8080 -c /app/openshift-acct-req/config.py -e PYTHONBUFFERED=TRUE wsgi:app

