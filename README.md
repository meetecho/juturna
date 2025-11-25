# Juturna – Real-time AI Pipeline Framework
<p align="center"><img src="https://raw.githubusercontent.com/meetecho/juturna/main/docs/source/_static/img/logo_dark_alt.svg" width="30%">
<br>
<img src="https://img.shields.io/github/license/meetecho/juturna?style=for-the-badge"> <img src="https://img.shields.io/github/stars/meetecho/juturna?style=for-the-badge"> <img src="https://img.shields.io/github/forks/meetecho/juturna?style=for-the-badge"> <img src="https://img.shields.io/github/issues/meetecho/juturna?style=for-the-badge">
</p>

## :seedling: Important to know
Juturna is actively evolving with exciting new features and improvements being
added regularly. We're using semantic versioning to clearly communicate any
breaking changes between releases, so you can upgrade with confidence. Juturna
is perfect for experimentation and prototyping today, and we're working toward
production-ready stability with each release. So, if you plan to deploy it in
production, make sure you are comfortable managing potential updates and
adjustments.

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

[documentation](https://meetecho.github.io/juturna/index.html) | [contribute](https://github.com/meetecho/juturna/blob/main/CONTRIBUTING.md) | [meetecho](https://www.meetecho.com/en/)

## Overview

A **pipeline** can simply be defined as a collection of **nodes**.

Each **node** acquires a piece of data from its parents and, after performing a
single task, provide its output to its children. In this sense, a Juturna
pipeline is nothing else but a DAG, where root nodes have an in-degree of 0
(this is not technically the case, but we’ll skip it for now), and every other
node has an in-degree of 1 or more.

An example of one of our pipelines, currently in use for live audio
transcription and summarisation is shown here.

<p align="center"><img src="https://raw.githubusercontent.com/meetecho/juturna/main/assets/img/pipeline_example.png"></p>

Whilst Juturna ships with a number of built-in nodes (mainly source and sink
nodes), you can implement your own nodes with ease, and share them so others
can use them too.

To know more about the Juturna internals, please refer to the full
documentation.

## Installation

The following dependencies are required to use Juturna:

- ``python >= 3.12``
- system libraries ``libsm6``, ``libext6``, ``ffmpeg``

:information_source: Current Python building version is 3.12. The library still
has to be tested on Python 3.13 and later with GIL disabled.


Juturna is currently available as a opensource codebase, but not yet published
on PyPi.  To install it on your system, first clone the repository, then use
pip to install it (assuming you are working in a virtual environment):

```
(venv) $ git clone https://github.com/meetecho/juturna
(venv) $ pip install ./juturna
```

In case you want to include all the development dependencies in the
installation, specify the ``dev`` group:

```
(venv) $ pip install "./juturna[dev]"
```

To include the Juturna HTTP wrapper, include the ``httpwrapper``:

```
(venv) $ pip install "./juturna[httpwrapper]"
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

Please read [`CONTRIBUTING.md`](https://github.com/meetecho/juturna/blob/main/CONTRIBUTING.md) for:

* Branching & PR workflow 
* Code style & linting
* Issue triage (TBD)
* Issue & PR templates and a Code of Conduct are provided (TBD)
* Signing CRA

## Changelog

All notable changes are documented in [`CHANGELOG.md`](https://github.com/meetecho/juturna/blob/main/CHANGELOG.md)
following [Semantic Versioning](https://semver.org).

## External Docs & Support

Coming soon!

## License

Distributed under the **MIT License**. See [LICENSE](https://github.com/meetecho/juturna/blob/main/LICENSE) for details.
