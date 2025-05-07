# Juturna – Real-time AI Pipeline Framework

[![License](https://img.shields.io/github/license/meetecho/juturna)](LICENSE)

**Juturna** is a data pipeline library written in Python. It is particularly useful for fast prototyping multimedia, **real-time** data applications, as well as exploring and testing AI models, in a modular and flexible fashion.

Throught **Juturna** it is possible to chain **nodes** in **unidirectional** workloads called **pipeline**

---

## Key Features

* 🎯 **Real-Time Streaming:** Continuous processing of audio, video and arbitrary data streams
* 🔌 **Modular Nodes:** !!! brief juturna_hub description 
* 🔗 **Composable workloads:** !!! brief description on pipelines
* 🛠️ **Extensible:** Create custom nodes by subclassing the `BaseNode` 
* 🚀 **Parallelism & Batching:** Optional concurrent execution for high throughput
* 📊 **Observability:** Built-in logging and metrics support

---

## Overview

A **pipeline** can simply be defined as a collection of **nodes**. 

Each **node** acquires a piece of data from its parent and, after performing a single task, provide its output to its children. In this sense, a Juturna pipeline is nothing else but a rooted tree, a particular kind of DAG where there is a single root node with in-degree of 0 (this is not technically the case, but we’ll skip it for now), and every other node has an in-degree of 1.

!!! Insert block image here

A node is a pipeline component that should, ideally, do one and only one thing. Depending on the task they are programmed to perform, nodes can be:

- source: they either consume external data (obtained from real-time streams, remote or local files, databases…) or generate data to push into the pipelline
- processing: they either transform, annotate or tag input data, or generate completely new data based on their input
- sink: they deliver the input data to a configured destination, either local or remote

---

## 5. Installation

The following dependencies are required to use Juturna:

| dependency |   type   | notes |
|------------|----------|-------|
| `python`   | `>=3.12` | building version is 3.12, still to be tested on 3.13 with GIL disabled |
| `libsm6`   | `system` | |
| `libext6`  | `system` | |
| `ffmpeg`   | `system` | |


Juturna is currently available as a opensource codebase, but not yet published on PyPi. 
To install it on your system, first clone the repository, then use pip to install it (assuming you are working in a virtual environment):

```
(venv) $ git clone https://github.com/meetecho/juturna
(venv) $ pip install ./juturna
```

In case you want to include all the development dependencies in the installation, specify the dev group:

```
(venv) $ pip install "./juturna[dev]"
```

Alternatively, you can manually install the required dependencies, and just import the juturna module from within the repository folder:

```
(venv) $ pip install av ffmpeg-python opencv-python numpy requests websockets
(venv) $ python
>>> import juturna as jt
```

### Dockerfile

In the Juturna repository you will find a Dockerfile that can be used to create a base Juturna image. To build it, symply navigate within the repo folder and run:

```
$ docker build -t juturna:latest .
```

---

## Quickstart

!!! Add a MWE 

---

## `juturna_hub`

!!! Add a description

---

## Juturna API

!!! Add a description

---

## Advanced Examples

See the [`plugins/pipelines/`](./plugins/pipelines/) folder for end-to-end use cases

---

## Testing

!!! Add the testing flow

---

## Contributing

Please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) for:

* Branching & PR workflow
* Code style & linting
* Issue triage
* Issue & PR templates and a Code of Conduct are provided.
* Signing CRA

---

## Changelog

All notable changes are documented in [`CHANGELOG.md`](./CHANGELOG.md) following [Semantic Versioning](https://semver.org).

---

## External Docs & Support

!!! add the full doc ref here

---

## License

Distributed under the **MIT License**. See [LICENSE](./LICENSE) for details.

---