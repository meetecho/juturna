# Agent guide

Guidance for coding agents working on this repository.

## Project

Juturna is a Python (>=3.12) library for building real-time data pipelines
(audio, video, arbitrary streams, AI model prototyping) as DAGs of modular
nodes. It is published as the `juturna` package. The official node
collection (`juturna.nodes`, including the `Warp` node) and contrib node
repositories (`juturna.contrib.<org>`) are separate distributions that
extend the `juturna` namespace.

The code is the source of truth. The Sphinx docs and older notes sometimes
describe removed features (the `mark` and `plugins` pipeline keys, a
`plugins/` folder, the hub, buffers and synchronisers). Check a description
against the code before relying on it, and fix the docs in the same change
when they disagree.

## Skills

The agent skills at <https://github.com/b3by/skills> are the working
agreement for this repository:

- `juturna-core`: changes to the library or its tests.
- `juturna-nodes`: writing or changing nodes.
- `python` and `python-tools`: code style and tooling, where this
  repository doesn't define its own (see below).
- `github-workflow`: the issue-first process, only when the owner asks for
  it. Agents never merge.
- `prerelease-review`: only on explicit request.

This file, `ruff.toml`, `pyproject.toml` and `CONTRIBUTING.md` take
precedence over the skills: Python 3.12+, pip with extras, and the
repository's own ruff configuration.

## Commands

```bash
# install with all features and dev tools
pip install -U -e ".[full,dev_full]"
pre-commit install && pre-commit install --hook-type commit-msg

# lint and format (CI runs both on PRs)
ruff check .
ruff format --check .

# tests, as CI runs them (ffmpeg must be installed)
pytest tests/ -q -W error::RuntimeWarning \
  --cov=juturna --cov-report=term-missing

# single test
pytest tests/test_node_threads.py::test_name -vvv

# security scan (manual hook)
pre-commit run --hook-stage manual bandit --all-files

# docs
sphinx-build -b html docs/source/ docs/build/html
```

- CI tests on Python 3.12, 3.13, 3.14 and free-threaded 3.14t. Code has to
  be correct without the GIL: run at least the affected tests on `3.14t`
  when touching concurrency.
- `-W error::RuntimeWarning` means unawaited coroutines and similar
  warnings fail CI.
- Tests for optional features skip when their extra isn't installed: say
  which ones skipped.
- `pytest --keep-data` keeps the pipeline folders written under
  `tests/running_pipelines`.

## Style

- `ruff.toml` is the source of truth: line length 80, **single quotes**,
  pydocstyle (`D`) rules with NumPy-style docstrings
  (`Parameters\n----------`). It doesn't enable the I/N/PTH rules that
  `CONTRIBUTING.md` mentions, so don't reformat imports you aren't otherwise
  changing.
- Package `__init__.py` files start with `# noqa: D104` and re-export the
  implementations in private `_module.py` files through `__all__`.
- Commits follow Conventional Commits
  (`feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`, optional
  scope, lowercase imperative subject), enforced by a commit-msg hook and in
  CI. release-please builds the version and `CHANGELOG.md` from them: never
  bump the version or edit the changelog by hand.

## Architecture

```text
juturna/
  components/   Pipeline, Node, Message, State, DAG, node builder,
                pipeline exceptions
  payloads/     frozen payload dataclasses and Draft
  transport/    TransportBackend protocol; threading and browser backends
  telemetry/    telemetry managers: memory, csv, browser
  remotizer/    protobuf wire format and converters for remote nodes
  cli/          python -m juturna commands, HTTP service, PipelineManager,
                remote node service (remotize)
  meta/         tunable constants, overridable by environment variables
  names/        StrEnum status names
  utils/        logging, env vars, safe names, networking helpers
```

### Pipeline lifecycle (`components/_pipeline.py`)

A `Pipeline` is built from a JSON config (`{"version", "pipeline": {"name",
"id", "folder", "nodes": [...], "links": [{"from", "to"}], "transport"?,
"telemetry"?}}`; see `tests/test_pipelines/*.json`). Status moves
NEW → `warmup()` → READY → `start()` → RUNNING → `stop()` → STOPPED →
`destroy()` → DESTROYED. Each method enforces its transition and raises a
`PipelineStateError` subclass (a `RuntimeError`) otherwise.

- `warmup()` writes `config.json`, gives each node its own subfolder under
  `folder`, builds the nodes, wires links (`add_destination` and `origins`),
  rejects duplicate names and cycles (`_dag.py`), creates one `State` per
  node, sets up telemetry and calls each node's `warmup()`. A failing
  `warmup()` or `start()` rolls back what it already did; keep those paths
  working and tested.
- `start()` walks the DAG layers from `BFS()` in **reverse** (sinks first,
  sources last). `stop()` walks them forward, stopping and joining one layer
  at a time, so upstream nodes stop before downstream ones.
- `update_node(name, prop, value)` calls the node's `set_on_config`.
- A node with `"warped": true` is replaced by the `Warp` node of the
  official collection: its `warp_configuration` becomes the configuration,
  the original `configuration` goes into `remote_config`, and `sticky`
  (default `true`) says whether the remote service keeps the node state.

### Node building (`components/_node_builder/`)

- `type` is a dotted path: one starting with `extensions` or `contrib` is
  imported under `juturna.`, anything else under `juturna.nodes.`. The last
  segment is the class name, read from the package registry
  (`_AVAILABLE_PLUGINS`, lazy-loaded through `_lazy_node_loaders`).
- Each node ships a `config.toml` whose `[arguments]` table lists the
  allowed constructor kwargs and their defaults. The pipeline
  `configuration` overrides only keys that exist there; unknown keys are
  dropped silently. A string value `$JT_ENV_<NAME>` is read from the
  environment, cast to the default's type, and errors if unset.
- The builder always passes `node_name`, `pipe_name` and `transport`, so a
  node's `__init__` must accept `**kwargs` and call
  `super().__init__(**kwargs)`. `configure()` runs right after construction.

### Node runtime (`components/_node.py`)

`Node[T_Input, T_Output]` runs up to two workers, spawned from the
transport:

- `_worker` takes each message from the input queue, records `rx`
  telemetry and calls `update(message, state=...)` directly.
- `_source` runs only after `set_source(fn, by, mode)`: it calls `fn` in a
  loop and feeds the results to the node's own queue, with an exponential
  backoff on errors.

Exceptions in user code are caught, counted in `health` and logged; the
worker keeps running. Don't swallow exceptions anywhere else. `transmit()`
freezes the `Message` and `put`s it to every destination. Subclasses
override `configure`/`warmup`/`update`/`destroy`/`set_on_config`; if they
override `start`/`stop`, they must call `super()`.

Two hooks serve the remote service and aren't meant for node authors:
`link_state_resolver(fn)` picks the state for each message (returning
`Node.SKIP_UPDATE` drops it), and `link_update_observer(fn)` is called after
every `update()` with the message and the exception or `None`.

### Multiple inputs and state

There is no buffer or synchroniser. Messages from every upstream node reach
`update()` one at a time, in queue order; `message.creator` tells them
apart. A node that needs several messages before producing an output keeps
the pending ones in `kwargs['state']` (the pipeline-owned `State`, which
outlives the node's `stop()` and `kill()`) and evicts them itself.

### The node contract is public API

External node packages depend on the `Node` hooks and helpers, the delivery
model above, `Message`, the payloads and `Draft`, the builder rules,
`_lazy_node_loaders`, the `juturna.meta` constants and the remote protocol.
Changing any of them is breaking: mark the commit with `!` and a
`BREAKING CHANGE:` footer, update the docs, and list the affected node
packages.

### Transport (`transport/`)

Components never import `threading`, `queue` or `multiprocessing`. They get
queues, events, locks, conditions and workers from the `TransportBackend`
protocol (`_base.py`). The pipeline picks the backend with
`get_transport(config['pipeline'].get('transport'))`; the registry
(`_registry.py`) has `threading` (default) and `browser` (Pyodide workers
over `SharedArrayBuffer` and JSPI). Queue timeouts raise
`juturna.transport.Empty`, full queues `juturna.transport.Full`.

- Protect shared state with a transport lock or condition; don't rely on
  the atomicity of list, dict or counter operations.
- Put a timeout on every blocking call (`JUTURNA_THREAD_JOIN_TIMEOUT`), and
  make every worker loop check its stop event.
- Import `js` and `pyodide` lazily, so the browser backend imports on a
  desktop interpreter.

### Remote nodes (`cli/commands/_juturna_remote_service.py`, `remotizer/`)

`python -m juturna remotize` (the `warp` extra) builds one node and serves
it over gRPC to `Warp` clients. `remotizer/protos/` defines the wire
format, `remotizer/c_protos/` holds the generated code, and
`remotizer/utils.py` converts messages, payloads and states.

- Each request carries one message; the service answers when `update()`
  returns, with the first message transmitted or none.
- Sticky clients' state stays on the service; stateless clients send it
  with every request. Support both.
- Values keep their types on the wire. What can't be sent is left out with
  one warning per client and kind of loss, or fails with `DATA_LOSS` under
  `--strict`. Never drop data silently.
- After editing `remotizer/protos/*.proto`, run `./compile_protos.sh` from
  `juturna/remotizer` (needs `grpcio-tools`) and commit the generated files.
  A protocol change is breaking for every `Warp` client.

### Messages, payloads and configuration

- `Message` (`components/_message.py`) has a global `itertools.count` id,
  reset in tests by an autouse fixture.
- Payloads (`juturna/payloads`) are frozen dataclasses (`AudioPayload`,
  `ObjectPayload`, `Batch`, ...) exposing `size_bytes` for telemetry; `Draft`
  is the mutable builder form. A new payload type also needs `serialize`,
  `Draft` support, a path through every transport, and a protobuf message
  with converters in the remotizer.
- Tunables live in `juturna/meta/_constants.py` and can be overridden by an
  environment variable of the same name. Don't hardcode timeouts or sizes.
- Pipeline, node and telemetry file names become paths: check them with
  `juturna.utils.jt_utils.check_name`.
- Add a backend (transport, telemetry manager, CLI command) by implementing
  its protocol and adding it to its registry, not by special-casing callers.

### CLI and service

- `juturna/cli`: `python -m juturna <cmd>`. Commands (`launch`, `validate`,
  `serve`, `create`, `stub`, `remotize`) are listed in
  `cli/commands/__init__.py` (`_MODULES`) and register only if their module
  imports, so a command whose extra is missing doesn't appear.
- `serve` runs a FastAPI app (`httpwrapper` extra) backed by the
  `PipelineManager` singleton (`cli/commands/_pipeline_manager.py`). It
  authenticates with a bearer token, validates configs with pydantic models
  (`cli/commands/models/api/`), confines pipeline folders to its base
  folder, and resolves only allowlisted environment variables.

## Tests

- Tests live flat in `tests/`, one file per area.
- Test-only nodes (sequencer, crasher, dumper, aggregator, ...) live in
  `tests/_nodes/juturna/contrib/jt_test/nodes/`, found through
  `pythonpath = ["tests/_nodes"]`. Use them as
  `contrib.jt_test.nodes.<Class>`, and add a new one there when none fits.
- Pipeline JSON fixtures live in `tests/test_pipelines/`.
- Wait with the `wait_for_condition` fixture and a timeout, never a fixed
  `sleep`.
- Every bug fix gets a regression test; concurrency fixes get one that fails
  without the fix under load or on `3.14t`.
