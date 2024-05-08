FROM python:3.12-slim

RUN apt update && apt upgrade -y;

COPY ./app /app

RUN pip install -r /app/requirements.txt

ENTRYPOINT [ "tail", "-f", "/dev/null" ]
