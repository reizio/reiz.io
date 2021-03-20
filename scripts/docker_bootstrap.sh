#!/usr/bin/bash
set -xe

# create the structure
mkdir -p /app/tmp/data
mkdir -p ~/.local/

# copy the config
cp static/configs/docker_config.json ~/.local/reiz.json

# create the dataset
python -m reiz.sampling.get_dataset \
          --limit 1 /app/tmp/dataset.json

# fetch the dataset
python -m reiz.sampling.fetch_dataset \
          /app/tmp/dataset.json /app/tmp/data \
          --ignore-tests

# await database
sleep 5

# shape the db
bash /app/scripts/regen_db.sh

# serialize the dataset
python -m reiz.serialization.serialize --fast \
          /app/tmp/dataset.json /app/tmp/data

# start the webserver
python -m reiz.web.asgi
