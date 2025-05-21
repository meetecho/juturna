# Juturna – Real-time AI Pipeline Framework

[![License](https://img.shields.io/github/license/meetecho/juturna?style=for-the-badge)](LICENSE)
![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fmeetecho%2Fjuturna%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&style=for-the-badge&color=green)

[![Stars](https://img.shields.io/github/stars/meetecho/juturna?style=for-the-badge)](STARS)
[![Forks](https://img.shields.io/github/forks/meetecho/juturna?style=for-the-badge)](FORKS)
[![issues](https://img.shields.io/github/issues/meetecho/juturna?style=for-the-badge)](ISSUES)

## :rotating_light: Disclaimer
Juturna is still under **heavy development**, so there might be breaking changes
along the way. We also recommend, for the moment, using Juturna in
experimenting and prototyping scenarios. Please be sure you know what you are
doing if you want to deploy Juturna in a production environment.

## At a glance

**Juturna** is a data pipeline library written in Python. It is particularly
useful for fast prototyping multimedia, **real-time** data applications, as
well as exploring and testing AI models, in a modular and flexible fashion.

Among its many features, there are a few keypoints to highligh about Juturna:

* :zap: **Real-Time Streaming:** continuouusly process audio, video and
  arbitrary data streams
* :electric_plug: **Modularity:** create your own nodes and share them through
  the Juturna hub
* :link: **Composable workloads:** design pipelines to solve complex tasks in
  minutes
* 🚀 **Parallelism & Batching:** parallel, non-blocking execution for high
  throughput
* 📊 **Observability:** built-in logging and metrics support


## Overview

A **pipeline** can simply be defined as a collection of **nodes**.

Each **node** acquires a piece of data from its parent and, after performing a
single task, provide its output to its children. In this sense, a Juturna
pipeline is nothing else but a rooted tree, a particular kind of DAG where
there is a single root node with in-degree of 0 (this is not technically the
case, but we’ll skip it for now), and every other node has an in-degree of 1.

An example of one of our pipelines, currently in use for live audio
transcription and summarisation is shown here.

![juturna entities](./assets/img/pipeline_example.png?raw=true)

Whilst Juturna ships with a number of built-in nodes (mainly source and sink
nodes), you can implement your own nodes with ease, and share them so others
can use them too.

To know more about the Juturna internals, please refer to the full
documentation.

## Installation

The following dependencies are required to use Juturna:

| dependency |   type   | notes |
|------------|----------|-------|
| `python`   | `>=3.12` | building version is 3.12, still to be tested on 3.13 with GIL disabled |
| `libsm6`   | `system` | |
| `libext6`  | `system` | |
| `ffmpeg`   | `system` | |


Juturna is currently available as a opensource codebase, but not yet published
on PyPi.  To install it on your system, first clone the repository, then use
pip to install it (assuming you are working in a virtual environment):

```
(venv) $ git clone https://github.com/meetecho/juturna
(venv) $ pip install ./juturna
```

In case you want to include all the development dependencies in the
installation, specify the dev group:

```
(venv) $ pip install "./juturna[dev]"
```

Alternatively, you can manually install the required dependencies, and just
import the juturna module from within the repository folder:

```
(venv) $ pip install av ffmpeg-python opencv-python numpy requests websockets
(venv) $ python
>>> import juturna as jt
```

### Dockerfile

In the Juturna repository you will find a Dockerfile that can be used to create
a base Juturna image. To build it, symply navigate within the repo folder and
run:

```
$ docker build -t juturna:latest .
```

## Contributing

Please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) for:

* Branching & PR workflow 
* Code style & linting (TBD)
* Issue triage (TBD)
* Issue & PR templates and a Code of Conduct are provided (TBD)
* Signing CRA

## Changelog

All notable changes are documented in [`CHANGELOG.md`](./CHANGELOG.md)
following [Semantic Versioning](https://semver.org).

## External Docs & Support

Coming soon!

## License

Distributed under the **MIT License**. See [LICENSE](./LICENSE) for details.
