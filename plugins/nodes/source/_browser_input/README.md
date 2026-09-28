# browser_input

Source node fed by the web page hosting a browser-only pipeline
(Pyodide + `BrowserTransport`).

## Node type: source

## Node class name: BrowserInput

## Node name: browser_input

## How it works

The node sets no source function. The page hands a message over to the
Worker, the Worker calls `feed(js_message)` on the node, and the node puts
the decoded message on its own queue, like `file_watcher` does with
filesystem events. The wire format is defined in
`juturna/transport/_browser_io.py`.

`feed()` blocks when the queue is full, so it must be invoked through
`.callPromising()`. Concurrent `feed()` calls may be reordered: the host
should serialise them (a promise chain in JS) whenever order matters, as it
does for audio.

## Arguments

None.

## Input message

Not a Juturna message: a JS object `{kind, payload, meta}` passed to
`feed()`.

- `kind` (required): `audio`, `image`, `bytes` or `object`. Any other value
  raises `ValueError`.
- `payload`: the fields of the matching payload. Unknown fields raise
  `ValueError`; a missing field takes the payload default.
  - `audio`: `audio` (`Float32Array`, or `Int16Array`, normalised to
    [-1, 1]), `sampling_rate`, `channels`, `start`, `end`,
    `audio_format`. In practice `audio` and `sampling_rate` are the ones
    downstream nodes need.
  - `image`: `image` (flat `Uint8Array`), `width`, `height`, `depth`,
    `pixel_format`, `timestamp`. `width`, `height` and `depth` are needed
    to rebuild the `(height, width, depth)` array; without them the image
    stays flat.
  - `bytes`: `cnt` (`Uint8Array`).
  - `object`: any JSON-compatible fields.
- `meta` (optional): copied into the message `meta`. No key is required.

## Output message

The decoded message, forwarded unchanged by `update()`.

- Payload: `AudioPayload`, `ImagePayload`, `BytesPayload` or
  `ObjectPayload`, according to `kind`. Arrays are copied into Python
  memory (`np.float32` for audio, the sent dtype for images).
- `creator`: the node name.
- `meta`: exactly the `meta` sent by the page. The node adds nothing.
