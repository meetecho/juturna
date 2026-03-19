# summarizer_ollama

This node queries an ollama endpoint to produce interative summaries.

The expected input is an object structured as follows:

```json
{
    "topic": <TOPIC>,
    "chunk": <TEXT>
}
```

The node will store the response history for any specific content, using them
whenever a new chunk for that content is available. For instance:

```
input_1: { topic: topic_1, chunk: chunk_1 }
ollama(input_1) --> { summary: summary_1 }

input_2: { topic: topic_1, chunk: chunk_2 }
ollama(summary_1, input_2) --> { summary: summary_2 }

input_3: { topic: topic_2, chunk: chunk_1 }
ollama(input_3) --> { summary: summary_1 }

...
```

When configuring the node, it can be specified how many topics the node should
follow, and the policy to delete a topic whenever there are no more available
slots. Additionally, the maximum length for topic history can be set.

To give an example, if a summarizer is set to follow 3 topics, its history
object will be considered full once three separate topics were passed. Assuming
`topic_1`, `topic_2` and `topic_3` are provided to the node at some point, the
node history will look like this:

```json
{
    "topic_1": [<summary_1>, <summary_2>, ... <summary_n>],
    "topic_2": [<summary_1>, <summary_2>, ... <summary_n>],
    "topic_3": [<summary_1>, <summary_2>, ... <summary_n>]
}
```

This node can also be configured with a static list of topics to be followed,
defined with the `include` configuration item. Similarly, excluded topics can
be defined in the `exclude` configuration list.

The node can work with multiple sources, however, topics should be specific to
sources. This means, if node `source_0` is producing messages for `topic_0` and
`topic_1`, then messages for those topics are not expected to be generated from
any other sources.

## Node type: proc

## Node class name: SummarizerOllama

## Node name: summarizer_ollama
