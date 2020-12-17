#!/usr/bin/bash

./scripts/generate_schema.py static/Python-reiz.asdl > static/Python-reiz.edgeql
./scripts/reset_db.py static/Python-reiz.edgeql
