FROM python:3

WORKDIR /app

ADD . /app
RUN mkdir /app/archives

RUN wget -qO - https://www.mongodb.org/static/pgp/server-3.6.asc | apt-key add -
RUN echo "deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/3.6 main" | tee /etc/apt/sources.list.d/mongodb-org-3.6.list

RUN apt-get update
RUN apt-get install -y mongodb-org-tools
RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 5003

ENV ARCHIVE_PATH /app/archives
ENV ONTOLOGY_ACTIVE canonical-v.1.0.0
ENV AWS_ACCESS_KEY_ID ???
ENV AWS_SECRET_ACCESS_KEY ???

VOLUME /app/archives

CMD ["python", "-m", "ont.service"]