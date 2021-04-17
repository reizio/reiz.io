#!/usr/bin/bash

./scripts/generate_schema.py static/Python-reiz.asdl static/Python-reiz.esdl static/Python-reiz.json
./scripts/generate_fielddb.py static/Python-reiz.asdl > static/Python-reiz-fielddb.json
./scripts/reset_db.py static/Python-reiz.esdl --dont-reboot-server
