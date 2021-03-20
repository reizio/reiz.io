FROM python:3.8.2-slim

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install git apt-utils bash -y

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

COPY . .
RUN python -m pip install -e .

ENTRYPOINT ["/bin/bash", "./scripts/docker_bootstrap.sh"]

