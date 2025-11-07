Messages and payloads
=====================

The Message class is Juturna's fundamental unit of data transfer. Messages are
designed to carry data payloads decorated with versioning, timing, and arbitrary
metadata. Every byte that flows through a pipeline flows inside a message.

Typed envelopes
---------------

A message wraps a generic payload of type ``T_Input``, with a consistent set of
headers. This envelope pattern provides several benefits:

- **Type safety**: the generic parameter communicates the expected data type to
  downstream nodes
- **Separation of concerns**: payload processing is decoupled from metadata
  tracking
- **Observability**: every message carries its own timing and provenance data