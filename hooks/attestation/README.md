# Handoff Attestation

Locks approved handoff files with SHA-256 so context-injection hooks do not feed tampered instructions back into the model.

## Usage

```bash
# Attest active .handoffs/<ADR>/input-package.yaml if present, else HANDOFF-PROTOCOL.md
.github/hooks/attestation/attest-handoff.sh

# Attest a specific file
.github/hooks/attestation/attest-handoff.sh .handoffs/ADR-2026-05-example/input-package.yaml
```

Attestation files:

- `.handoffs/<ADR>/.attestation` for `input-package.yaml`.
- `.handoffs/.protocol-attestation` for `HANDOFF-PROTOCOL.md`.

