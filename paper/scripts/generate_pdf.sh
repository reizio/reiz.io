#!/usr/bin/bash
set -xe

# formatting
mdformat --wrap 79 source/content.md
biber --tool --output_align --output_indent=4 --output_fieldcase=lower source/paper.bib
mv source/paper_bibertool.bib source/paper.bib
rm source/paper.bib.blg

# prepare for build
cat source/header.md source/content.md source/evaluation.md source/footer.md > paper.md
cp source/paper.bib .
cp source/assets/* .

# build
docker run --rm \
    --volume $PWD:/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/paperdraft

# show
firefox paper.pdf
