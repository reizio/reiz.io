#!/usr/bin/bash

./scripts/generate_schema.py static/Python-reiz.asdl static/Python-reiz.edgeql static/Python-reiz.json
./scripts/generate_fielddb.py static/Python-reiz.asdl > static/Python-reiz-fielddb.json
./scripts/reset_db.py static/Python-reiz.edgeql --dont-reboot-server
