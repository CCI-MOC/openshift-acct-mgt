FROM python:3.11

RUN mkdir -p /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# If you are building an image locally, note that this will copy
# all files from the current directory into the image, including
# those that are not part of the repository. This is not an issue
# when building the image in CI (or in an OpenShift Build).
COPY . ./

CMD ["/app/start.sh"]

