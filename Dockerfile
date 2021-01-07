FROM python:3.6-slim-buster

WORKDIR /usr/src/app

COPY . reactive-uart2ip/
RUN reactive-uart2ip/install_docker.sh && rm -rf reactive-uart2ip
