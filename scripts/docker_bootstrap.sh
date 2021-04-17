pre_db () {
    # create the dataset
    python -m reiz.sampling.get_dataset \
              --limit 10 /app/tmp/dataset.json

    # fetch the dataset
    python -m reiz.sampling.fetch_dataset \
              /app/tmp/dataset.json /app/tmp/rawdata

    # sanitize the dataset
    python -m reiz.sampling.sanitize_dataset \
              /app/tmp/dataset.json /app/tmp/rawdata \
              /app/tmp/data --ignore-tests
}

post_db () {
    # shape the db
    python /app/scripts/create_db.py

    # serialize the dataset
    python -m reiz.serialization.insert --fast \
              --limit 56 --project-limit 7 /app/tmp/dataset.json
}

#!/usr/bin/bash
set -xe

# create the structure
mkdir -p /app/tmp/data
mkdir -p ~/.local/

# copy the config
cp static/configs/docker_config.json ~/.local/reiz.json

pre_db
sleep 15 # await database
post_db

# start the webserver
python -m reiz.web.api
