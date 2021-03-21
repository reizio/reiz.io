FROM python:3.8.2-slim

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install git apt-utils -y

RUN git clone https://github.com/treescience/search.tree.science
WORKDIR search.tree.science
ENTRYPOINT ["python", "-m", "http.server", "8080"]
