FROM python:3.8

RUN mkdir -p /app
WORKDIR /app

COPY wsgi.py /app/wsgi.py
COPY moc_openshift.py /app/moc_openshift.py
COPY start.sh /app/start.sh
COPY requirements.txt /app/requirements.txt
COPY config.py /app/config.py

RUN cd /app \
 && pip3 install -r requirements.txt 

CMD ["/app/start.sh"]

