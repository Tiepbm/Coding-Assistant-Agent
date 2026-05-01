# Skill-Pack Quality Rubric — Coding Assistant

A PR that adds or edits a pack must clear these gates before merge.

| Gate | Bar |
|---|---|
| **Trigger accuracy** | `When to Use` triggers are concrete (≥ 3 examples), specific (mention API/tool/pattern), and routable (a model can match a user prompt to one trigger ≥ 80% of the time). |
| **Reference precision** | Each reference has a single `Use when` trigger; no two references in the same pack share the same trigger; references compose (one task = ≤ 3 references). |
| **Progressive disclosure** | Pack `SKILL.md` ≤ 100 lines, no inline code blocks. References ≤ 250 lines, with code blocks. Shim `*-handoff.md` ≤ 60 lines, no implementation code. |
| **Benchmark coverage** | New reference has at least 1 case in `coding-benchmark.jsonl` OR `handoff-benchmark.jsonl`. New anti-pattern has 1 case in `anti-pattern-benchmark.jsonl`. |
| **Originality** | Reference does not copy > 5 lines from another reference; uses `→` link instead. Reference does not copy from `software-engineering-agent` packs; uses shim `*-handoff.md` instead. |
| **Copilot readiness** | `.github/skills/<pack>/SKILL.md` mirror updated; `.github/copilot-instructions.md` mentions the pack; `validate_packs.py` passes. |
| **Senior-judgment alignment** | Implementation reference includes BAD/GOOD pair, error handling, runnable test, security defaults (parameterized queries, tenant authz, no secrets). Shim ref includes always-on rules + escalation table. |
| **Handoff awareness** | If the topic touches an architecture/governance decision (vendor, SLO, public API, tenant strategy, FinOps), the pack routes to a `*-handoff.md` shim that escalates to a specific CE7 reference path. |

## Severity for failed gates

- **S1 (block merge)**: Trigger accuracy, Benchmark coverage, Senior-judgment alignment, Handoff awareness.
- **S2 (block merge unless explicitly approved)**: Reference precision, Originality, Copilot readiness.
- **S3 (warn only)**: Progressive disclosure (legacy refs > 250 lines that pre-date the cap).

## Quick checklist for reviewers

- [ ] `validate_packs.py` PASS
- [ ] `validate-references.py` PASS
- [ ] At least 1 new benchmark case for new content
- [ ] No copy-paste > 5 lines from another reference
- [ ] If architecture-adjacent: shim `*-handoff.md` exists and links to CE7
- [ ] `.github/` mirror updated in the same PR
