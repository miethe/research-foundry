---
routing_workspace: "wiki"
routing_artifact_type: "concept"
routing_tags:
  - "agent-authored"
  - "transformer-architecture"
  - "attention-mechanism"
routing_project: "ml-foundations"
agent_origin: "claude-code"
automation_source: "research-synthesis-workflow"
parent_artifact_id: null
parent_run_id: null
---

# Attention Mechanism

The attention mechanism allows neural networks to focus on relevant parts of the input sequence when producing an output. Unlike fixed-context recurrent networks, attention computes a weighted sum over all encoder hidden states, where weights reflect learned relevance to the current decoding step.

## Key Properties

- **Query-Key-Value structure:** attention weights derived from dot product of query against keys; values are aggregated by those weights
- **Self-attention:** queries, keys, and values all derived from the same sequence (as in the Transformer encoder)
- **Multi-head attention:** multiple parallel attention heads capture different relationship types across the same sequence

## Related Concepts

- Transformer architecture
- Scaled dot-product attention
- Positional encoding
