---
name: working-memory-synchronizer
description: >
  Synchronizes working memory with project state. Invoke after completing a feature,
  making an architectural decision, or when activeContext.md feels stale.
  Can also be triggered with /update-working-memory.
---

# Working Memory Synchronizer

Invoke the `update-working-memory` skill through the host's skill mechanism. It contains the canonical process and file rules.

This agent is a thin wrapper so the workflow is reachable as a custom agent in hosts that surface one. The skill is the source of truth—do not duplicate process or rules here.
