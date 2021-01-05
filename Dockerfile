FROM python:3.6

WORKDIR /usr/src/app

COPY . reactive-uart2ip/
RUN reactive-uart2ip/install_docker.sh
