#!/usr/bin/bash

python -m reiz.db.schema_gen static/Python-reiz.asdl > static/Python-reiz.edgeql
python -m reiz.db.reset static/Python-reiz.edgeql
