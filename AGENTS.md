# AGENTS.md — Coding Assistant Contributor & Maintainer Guide

> Short, opinionated entry point for **humans** editing this repo. For full feature docs see `README.md`. For runtime behaviour see `agents/coding-assistant.agent.md`. For the contract with the principal-level `software-engineering-agent`, see `HANDOFF-PROTOCOL.md`.

## What this repo is

A Copilot-first **senior+ implementer** agent package, designed to pair with the principal-level `software-engineering-agent` (CE7):

- **1 router agent** — `agents/coding-assistant.agent.md`. Trim, table-driven, 6-step workflow with Clarify-First + Self-Review.
- **10 pack skills** — `skills/<pack>/SKILL.md`. Each pack routes to its own deep references.
- **Many references** — `skills/<pack>/references/*.md`. Implementation playbooks, BAD/GOOD pairs, with tests.
- **Examples** — `examples/`. End-to-end output shapes (TDD cycle, debugging, fullstack, perf, security, refactor).
- **Instructions** — `instructions/coding-standards.instructions.md`, `instructions/pack-conventions.instructions.md`. Maintainer-only conventions.
- **Eval harness** — `evals/{coding,debugging,tdd,handoff,anti-pattern}-benchmark.jsonl`, `evals/rubric.md`, `evals/run_eval.py`, `evals/validate-references.py`.
- **Validator** — `scripts/validate_packs.py` (CI-enforceable, mirrors structure check from CE7).
- **Handoff contract** — `HANDOFF-PROTOCOL.md`, byte-mirrored from the `software-engineering-agent` repo.

## Repo layout

```
agents/                 coding-assistant.agent.md  ← router; KEEP SHORT (~300 lines max)
skills/<pack>/SKILL.md  ← 10 packs; ≤ 100 lines each (validator-enforced)
skills/<pack>/references/*.md  ← implementation playbooks; ≤ 250 lines each
instructions/           coding-standards.instructions.md          ← runtime style + perf budget + dependency policy
                        pack-conventions.instructions.md          ← maintainer conventions for SKILL.md
                        principal-agent-maintenance.instructions.md   ← rules for editing agents/*.agent.md
                        principal-skills-maintenance.instructions.md  ← rules for editing skills/**/SKILL.md
examples/               implement-, debug-, tdd-, fullstack-, perf-, refactor-, security- shapes
evals/                  coding/debugging/tdd benchmarks, handoff & anti-pattern benchmarks, rubric, runner
scripts/validate_packs.py
docs/                   GETTING-STARTED, INSTALL, pipeline-guide, evaluation-improvement-playbook, skill-pack-quality-rubric
memory/                 README, learned-patterns, interaction-log, routing-corrections (agent self-improvement memory)
.github/                Copilot mirror (kept in sync with skills/ + agents/)
HANDOFF-PROTOCOL.md     ← mirrored from software-engineering-agent; CE7 is canonical owner
```

## Editing rules (the short version)

### Pack `SKILL.md` (≤ 100 lines)

A pack `SKILL.md` MUST contain — in this order — and NOTHING ELSE:

1. Frontmatter with `name` matching folder, `description` starting with `'Use when …'`.
2. `# <Pack Title>`.
3. `## When to Use` (3–6 concrete trigger bullets).
4. `## When NOT to Use` (2–4 anti-triggers pointing at neighbour packs OR escalation to CE7).
5. `## Pack Reference Map` (table; one row per reference; **distinct** `Use when` per row).
6. `## Cross-Pack Handoffs` (`→ <other-pack>` and `→ software-engineering-agent/skills/<pack>/references/<ref>` for CE7 escalations).

DO NOT add `Purpose`, `Routing Rules`, `Reference Selection Matrix`, `Expected Output Style`, `Token Efficiency Rules`, or `Quality Gates` sections — those live in `instructions/pack-conventions.instructions.md`.

### Reference (`references/*.md`)

- Frontmatter (`name`, `description` starting with `'Use when …'`).
- ≤ 250 lines (warn at 220).
- Always include: BAD pattern → GOOD pattern with 1-line reasoning, imports/types/error handling, runnable test.
- For "shim" references that route to CE7 (`*-handoff.md`), keep ≤ 60 lines: 5-line summary + link to the CE7 reference that owns the design.

### Coding Assistant agent (`agents/coding-assistant.agent.md`)

- KEEP UNDER ~330 lines. The agent is a router + workflow + checklists, not a knowledge dump.
- Do NOT inline content already covered by a pack/reference. If you write > 5 lines that duplicate a pack, replace it with `→ <pack-name>/<reference-name>`.
- The 6-step workflow (Clarify → Plan → Test-first → Implement → Self-Review → Verify), Clarify-First Protocol, Self-Review Checklist, Production Readiness Mini-Bar, and Auto-Attach rules are **runtime-critical** — do not trim them without updating evals.
- Update the `Skill Routing` table when you add/remove a pack or reference; update `Tie-Break Rules` when a new ambiguity is identified; update `Expert Escalation` table when a new CE7 reference becomes the owner of a decision.
- **Mirror to `.github/agents/coding-assistant.agent.md` whenever the root agent changes.**

### Eval files

- `evals/coding-benchmark.jsonl` — every prompt has `expected_pack`, `expected_references`, `must_include`, `must_not_include`. Add `expected_clarifying_questions` and `expected_observability_hooks` for senior-judgment cases.
- `evals/handoff-benchmark.jsonl` — cases that intentionally exceed Coding's authority; agent must escalate to a specific CE7 reference (`expected_escalation_reference`).
- `evals/anti-pattern-benchmark.jsonl` — every prompt has `must_not_do` and `must_do`.
- Critical security/data-loss tasks listed in `evals/rubric.md → Critical Tasks` MUST always pass.

### Instruction files

- `coding-standards.instructions.md` is **runtime** (`applyTo: skills/**/references/*.md`). Edits affect agent output. Treat as production code.
- `pack-conventions.instructions.md`, `principal-agent-maintenance.instructions.md`, `principal-skills-maintenance.instructions.md` are **maintainer-only**. Edits affect contributors, not the runtime model.

## Workflow

```bash
# 1. Make your changes in skills/, agents/, instructions/, evals/, examples/, docs/.

# 2. Run the structural validator before committing.
python3 scripts/validate_packs.py

# 3. Run the cross-reference validator.
python3 evals/validate-references.py

# 4. Sync the Copilot mirror.
for pack in backend-pack frontend-pack mobile-pack database-pack api-design-pack \
            observability-pack testing-pack debugging-pack devops-pack quality-pack; do
  cp -R skills/$pack/SKILL.md  .github/skills/$pack/SKILL.md
  cp -R skills/$pack/references .github/skills/$pack/
done
cp agents/*.agent.md .github/agents/

# 5. (When eval harness is wired to your runner) re-run benchmarks.
python3 evals/run_eval.py \
  --benchmark evals/coding-benchmark.jsonl \
  --responses runs/$(date +%Y%m%d)/responses.jsonl \
  --report   runs/$(date +%Y%m%d)/report.json
```

## Common edits — quick recipes

| You want to… | Touch these files |
|---|---|
| Add a new pack | `skills/<pack>/SKILL.md` + add EXPECTED entry in `scripts/validate_packs.py` + agent `Skill Routing` + this file |
| Add a reference inside an existing pack | new `skills/<pack>/references/<ref>.md` + add row to that pack's `Pack Reference Map` + EXPECTED entry in validator + (optional) coding-benchmark case |
| Add a tie-break rule | edit agent `Tie-Break Rules` (one line) + add a `boundary-*` case to `coding-benchmark.jsonl` |
| Add a "must-not-do" pattern | edit relevant pack `When NOT to Use` + add a row to `evals/anti-pattern-benchmark.jsonl` |
| Add a CE7 escalation | new `*-handoff.md` shim ref + update agent `Expert Escalation` table + add a `handoff-*` case to `evals/handoff-benchmark.jsonl` |
| Update the handoff contract | edit `software-engineering-agent/HANDOFF-PROTOCOL.md` (canonical) + `cp` to this repo |

## Bilingual policy

Two tiers, enforced by review (not by the validator yet):

- **Bilingual (`.md` + `.vi-VN.md`)** — user-facing docs: `README`, `docs/GETTING-STARTED`, `docs/INSTALL`, `docs/pipeline-guide`, `docs/evaluation-improvement-playbook`, `evals/rubric` (when added).
- **EN-only** — runtime/maintainer docs: `agents/*.agent.md`, `skills/**/*.md`, `instructions/*.instructions.md`, `examples/*`, `evals/*.jsonl`, `scripts/*`, `HANDOFF-PROTOCOL.md` (mirrored as-is from CE7), `CHANGELOG.md`, this file.

When in doubt: if the doc is read by a runtime consumer (Copilot, validator, pipeline script) or describes pack/agent internals, keep it EN-only. If it is a human entry point, keep it bilingual.

## What NOT to do

- Do not paste reference content into the agent or into another pack. Use `→` routing.
- Do not skip the **Self-Review Checklist** in the agent file — it is the difference between "writes code" and "ships expert code".
- Do not add a pack just because a topic feels important. Add a reference inside an existing pack first; only split when the pack outgrows its scope.
- Do not edit `.github/skills/` or `.github/agents/` directly — they are mirrors, regenerated from `skills/` and `agents/`.
- Do not edit `HANDOFF-PROTOCOL.md` in this repo unless the change has already landed in `software-engineering-agent` (CE7 is the canonical owner).
- Do not commit the validator failing. CI rejects it; humans should too.
- Do not duplicate decisions that belong to CE7 (SLO targets, vendor selection, public API governance) — escalate via the table in the agent file.

## Where to read next

- `README.md` — full project overview, install modes, pipeline.
- `HANDOFF-PROTOCOL.md` — contract with CE7.
- `agents/coding-assistant.agent.md` — the runtime brain; understand it before editing anything.
- `instructions/coding-standards.instructions.md` — runtime style + performance budgets + dependency governance.
- `docs/pipeline-guide.md` — end-to-end benchmark execution.
- `docs/evaluation-improvement-playbook.md` — when and how to improve packs.

