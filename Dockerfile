FROM python:3.12-slim

RUN apt-get update && apt-get install -y libsm6 libxext6 ffmpeg
RUN pip install --upgrade pip
RUN mkdir /root/juturna

COPY ./juturna /root/juturna/juturna
COPY ./pyproject.toml /root/juturna
COPY ./README.md /root/juturna

RUN pip install /root/juturna
