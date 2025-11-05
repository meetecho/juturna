.. _rationale:

Rationale
=========

Before we delve into the nitty-gritty details of the Juturna internals, it is
essential to clear the air about what Juturna is, and whom it is designed for.

Put simply, Juturna is a library for **real-time**, **multimedia**
**fast protopying**. There are some concepts to unpack here, so let's do that
and get this out of the way.

Real-time
---------

The main idea behind Juturna is to catch and process data as soon as they are
available, allowing different components to transform them independenty from
one another. To do so, Juturna leverages the concept of pipeline, which should
not require much explaining (but will be discussed further in this documentation
nonetheless). In short, data enter and traverse a Juturna pipeline in real-time,
and the nodes within that pipeline work asynchronously.

Mutlimedia
----------

Juturna offers a number of built-in nodes, and we mantainers strive to collect
as many community plugins as possible. Among all this, a robust group of key
nodes are entirely devoted to handling multimedia data. This of course includes
audio and video sourcing (from both remote and local sources), audio and video
processing.

Fast-prototyping
----------------

Well, ok, the concept of how fast prototyping *really* is can be subjective. At
the end of the day, it all boils down with how familiar your are with the tools
of the trade you decide to pick up. On this regard, Juturna keeps an ace up the
sleeve: the library has almost no dependency. Don't get me wrong, there are a
few packages that are installed, but they do not intervene in Juturna's working
internals. This means, an overview of its core concepts is virtually everything
you need to be up and running!