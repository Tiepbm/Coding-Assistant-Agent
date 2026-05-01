# Installation

The Coding Assistant Agent is a **Copilot-first** package: drop it into a project that uses GitHub Copilot, or install globally for all projects.

## Prerequisites

- GitHub Copilot enabled in your IDE (VS Code, JetBrains, Neovim).
- Python 3.10+ (only required to run the validator and eval harness, not for the agent itself).
- `git` (to clone and to keep the `HANDOFF-PROTOCOL.md` in sync with `software-engineering-agent`).

## Install modes

### Mode A — Per-project (recommended)

Copy the `.github/` directory into the project root. Copilot will pick up the agent and skills automatically.

```bash
git clone https://github.com/Tiepbm/coding-assistant-agent.git /tmp/coding-assistant-agent
cp -r /tmp/coding-assistant-agent/.github your-project/.github
```

If your project already has `.github/`, merge instead:

```bash
cp -rn /tmp/coding-assistant-agent/.github/skills/ your-project/.github/skills/
cp -rn /tmp/coding-assistant-agent/.github/agents/ your-project/.github/agents/
cp /tmp/coding-assistant-agent/.github/copilot-instructions.md your-project/.github/copilot-instructions.md
```

### Mode B — Global (all projects)

Copy `agents/` and `skills/` into your user-level Copilot config (path varies per IDE).

```bash
cp -r coding-assistant-agent/agents/ ~/.config/copilot/agents/
cp -r coding-assistant-agent/skills/ ~/.config/copilot/skills/
cp coding-assistant-agent/HANDOFF-PROTOCOL.md ~/.config/copilot/HANDOFF-PROTOCOL.md
```

### Mode C — Pair install with `software-engineering-agent` (CE7)

For the full **principal + senior+** experience:

```bash
mkdir -p ~/copilot-agents && cd ~/copilot-agents
git clone https://github.com/Tiepbm/software-engineering-agent.git
git clone https://github.com/Tiepbm/coding-assistant-agent.git

# Verify HANDOFF-PROTOCOL.md is in sync
diff -q software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md
```

If they differ, sync from CE7 (canonical owner):

```bash
cp software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md
```

## Verify the install

Run the structural validator:

```bash
cd coding-assistant-agent
python3 scripts/validate_packs.py
```

Expected output:

```
PASS: coding-assistant pack layout is valid
- packs: 10
- references: 49
- agent: coding-assistant.agent.md (with Clarify-First, Self-Review, Mini-Bar, Auto-Attach, HANDOFF link)
- HANDOFF-PROTOCOL.md present
```

## First task

Open your IDE in a project where Copilot is active. Ask:

> Implement an idempotent payment-capture endpoint in Spring Boot 3, header `Idempotency-Key`, p99 < 300ms, behind feature flag `payments.idempotent_v2` rolled out 1%->10%->50%->100%.

Expected behavior:

1. Agent does NOT ask clarifying questions (the brief is complete).
2. Agent emits an 8-step plan.
3. Agent writes test-first, then implementation, then runs the Self-Review Checklist.
4. Agent's response ends with the **Production Readiness Mini-Bar** (5 lines: idempotency, observability, tenant authz, rollback, runbook line).

If any of the above is missing, the install is incomplete or the agent file was not picked up. Re-run the validator and check the IDE Copilot logs.

## Upgrading

```bash
cd coding-assistant-agent && git pull
# Re-copy mirror if you used Mode A or B
```

After every upgrade, also pull `software-engineering-agent` and re-sync `HANDOFF-PROTOCOL.md`.

## Uninstall

```bash
rm -rf your-project/.github/skills/{backend,frontend,mobile,database,api-design,observability,testing,debugging,devops,quality}-pack
rm -f your-project/.github/agents/coding-assistant.agent.md
```
