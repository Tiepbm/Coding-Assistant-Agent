# Learned Patterns

Append-only log of patterns discovered during PR review or eval runs. Each entry:

```
## YYYY-MM-DD: <one-line summary>
- Symptom: ...
- Root cause: ...
- Fix: ... (touched files: ...)
- Benchmark case: ... (added/updated case ID)
- Owner: ...
```

---

## 2026-05-01: Initial entry — agent baseline

- Symptom: agent jumps to code without Clarify-First.
- Root cause: pre-v1.2 workflow had no Clarify step.
- Fix: added 6-step workflow with Clarify-First Protocol in `agents/coding-assistant.agent.md`.
- Benchmark case: `code-030` (ambiguous spec triggers clarifying questions).
- Owner: maintainers.
