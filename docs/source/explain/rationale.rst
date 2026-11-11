.. _rationale:

Rationale
=========

Before we delve into the nitty-gritty details of the Juturna internals, it is
essential to clear the air about what Juturna is, and whom it is designed for.

Put simply, Juturna is a library for **real-time**, **multimedia**
**fast prototyping**. There are some concepts to unpack here, so let's do that
and get this out of the way.

Real-time
---------

The main idea behind Juturna is to catch and process data as soon as they are
available, allowing different components to transform them independently from
one another. To do so, Juturna leverages the concept of pipeline, which should
not require much explaining (but will be discussed further in this documentation
nonetheless). In short, data enter and traverse a Juturna pipeline in real-time,
and the nodes within that pipeline work asynchronously.

Multimedia
----------

Juturna comes with a collection of officially supported nodes, the
``juturna-nodes`` package, and anybody can publish more. Among all this, a
robust group of key nodes is entirely devoted to handling multimedia data. This
of course includes audio and video sourcing (from both remote and local
sources), and audio and video processing.

Fast-prototyping
----------------

Well, ok, the concept of how fast prototyping *really* is can be subjective. At
the end of the day, it all boils down to how familiar you are with the tools
of the trade you decide to pick up. In this regard, Juturna keeps an ace up the
sleeve: the core library has almost no dependencies (``numpy`` is the only
one), and only a handful of concepts. This means an overview of those
concepts is virtually everything you need to be up and running!
