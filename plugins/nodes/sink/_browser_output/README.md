# browser_output

Sink node delivering every message it receives to the web page hosting a
browser-only pipeline (Pyodide + `BrowserTransport`).

## Node type: sink

## Node class name: BrowserOutput

## Node name: browser_output

## How it works

`update()` encodes the message in the wire format of
`juturna/transport/_browser_io.py` and posts it to the page with the
Worker's `postMessage`. Arrays reach the page as typed arrays.

## Arguments

None.

## Input message

Any message whose payload is an `AudioPayload`, `ImagePayload`,
`BytesPayload` or `ObjectPayload`. Other payload types raise `TypeError`,
which the node logs and counts in `update_failures` without stopping.

- Audio: `audio` (flattened), `sampling_rate`, `channels`, `start`, `end`,
  `audio_format`.
- Image: `image` (flattened), `width`, `height`, `depth`, `pixel_format`,
  `timestamp`. A page needs `width`, `height` and `depth` to rebuild the
  image.
- `meta`: sent as JSON; values that are not JSON-compatible are converted
  with `str()`. No key is required.

## Output message

Nothing goes down the pipeline. The page receives, through `postMessage`:

```
{type: 'output', node: <node name>,
 message: {kind, payload, meta, creator, id, created_at}}
```

`kind` is `audio`, `image`, `bytes` or `object`, and `payload` carries the
fields listed above.
