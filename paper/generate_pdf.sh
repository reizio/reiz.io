#!/usr/bin/bash
set -xe

# formatting
mdformat --wrap 79 source/content.md
biber --tool --output_align --output_indent=4 --output_fieldcase=lower source/paper.bib
mv source/paper_bibertool.bib source/paper.bib
rm source/paper.bib.blg

# prepare for build
mkdir -p build/
cat source/header.md source/content.md source/evaluation.md > build/paper.md
cp source/paper.bib build/
cp source/assets/* build/

# build
docker run --rm \
    --volume $PWD/build:/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/paperdraft

# show
firefox build/paper.pdf
