FROM python:3.6-slim-buster

WORKDIR /usr/src/app

COPY . reactive-uart2ip/
RUN pip install reactive-uart2ip/ && rm -rf reactive-uart2ip
