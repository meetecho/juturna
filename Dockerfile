FROM python:3.12-slim

RUN pip install --upgrade pip
RUN mkdir /root/juturna
RUN mkdir /juturna

WORKDIR /root/juturna

COPY ./juturna ./juturna
COPY ./pyproject.toml .
COPY ./README.md .

ARG JT_VERSION="[full]"

RUN pip install "./$JT_VERSION"
