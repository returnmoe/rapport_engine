FROM python:3.11-alpine

WORKDIR /etc/rapport_engine
COPY ./etc/rapport_engine/agent.conf.yaml .

WORKDIR /opt/rapport_engine
COPY ./requirements.txt ./
COPY ./src/rapport_engine ./

RUN [ "pip", "install", "-r", "requirements.txt" ]

ENTRYPOINT [ "python", "/opt/rapport_engine" ]