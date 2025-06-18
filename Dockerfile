FROM python:3.12-slim

RUN apt-get update && apt-get install -y libsm6 libxext6 ffmpeg
RUN pip install --upgrade pip
RUN mkdir /root/juturna
RUN mkdir /juturna

WORKDIR /root/juturna

COPY ./juturna ./juturna
COPY ./pyproject.toml .
COPY ./README.md .
COPY ./plugins /juturna/plugins

RUN pip install .
