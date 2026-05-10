# Handoff State

Runtime state directory for CE7 ↔ Coding Assistant work.

Create this in a target project as `.handoffs/` when an ADR handoff is active.

```text
.handoffs/
├── .active
├── ADR-YYYY-MM-slug/
│   ├── input-package.yaml
│   ├── return-package.yaml
│   ├── re-engagements.jsonl
│   ├── .attestation
│   └── progress.md
└── history.jsonl
```

## Rules

- CE7 writes `input-package.yaml` from `HANDOFF-PROTOCOL.md §3`.
- Coding writes `return-package.yaml` from `HANDOFF-PROTOCOL.md §4`.
- Run `.github/hooks/attestation/attest-handoff.sh` after CE7 approves `input-package.yaml`.
- Hooks inject `input-package.yaml` only when attestation matches; otherwise they warn and block injection.

