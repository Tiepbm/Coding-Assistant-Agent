---
name: "Handoff Protocol Sync Check"
description: "Detect drift between CE7 and Coding HANDOFF-PROTOCOL.md copies"
on:
  schedule: "daily on weekdays"
  workflow_dispatch: true
permissions:
  contents: read
  issues: write
safe-outputs:
  create-issue:
    title-prefix: "[handoff-drift] "
    labels: [sync, protocol]
---

# Handoff Protocol Sync Check

Ensure both agent repos use the same handoff contract.

## Steps

1. Compare `software-engineering-agent/HANDOFF-PROTOCOL.md` and `coding-assistant-agent/HANDOFF-PROTOCOL.md` byte-for-byte.
2. If they differ, create an issue with a short diff and state that CE7 is canonical.
3. Suggested fix: `cp software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md`.

