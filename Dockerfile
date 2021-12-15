FROM python:3.8

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt 

COPY wsgi.py moc_openshift.py start.sh config.py .

CMD ["/app/start.sh"]

