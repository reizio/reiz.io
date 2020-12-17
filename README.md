# reiz.io - Syntactic Source Code Search

Reiz bootstrap guide
```
echo "{YOR_CONFIG}" > ~/.local/reiz.json

mkdir sampling_data

python -m reiz.sampling.get_dataset sampling_data/data.json
python -m reiz.sampling.fetch_dataset sampling_data/data.json sampling_data/raw
python -m reiz.sampling.sanitize_dataset sampling_data/data.json sampling_data/raw sampsampling_dataling/clean

./script/regen_db.sh

python -m reiz.serialization.serialize sampling_data/data.json sampling_data/clean/
./script/run_query test_query.reizql
```
