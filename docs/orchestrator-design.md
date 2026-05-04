# Orchestrator Design — CE7 ↔ Coding Assistant Handoff Automation

## Problem

Currently, handoff between CE7 and Coding Assistant requires manual copy-paste of YAML packages. Users must:
1. Ask CE7 for a decision → get Implementation Input Package
2. Manually paste that package into a Coding Assistant session
3. Get code back → manually paste the Self-Review Block back to CE7

This breaks flow and loses context.

## Solution: MCP-based Orchestrator

An MCP server that:
1. Exposes both agents as tools
2. Manages handoff state (YAML packages)
3. Routes requests to the correct agent based on boundary rules
4. Tracks conversation history per ADR

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  User (IDE)                       │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│           MCP Orchestrator Server                 │
│                                                   │
│  ┌─────────────┐    ┌──────────────────────┐    │
│  │ Router      │    │ Handoff State Store   │    │
│  │ (boundary   │    │ (ADR packages,        │    │
│  │  rules)     │    │  conversation log)    │    │
│  └──────┬──────┘    └──────────────────────┘    │
│         │                                        │
│  ┌──────▼──────┐    ┌──────────────────────┐    │
│  │ CE7 Agent   │    │ Coding Agent          │    │
│  │ (decisions) │◄──►│ (implementation)      │    │
│  └─────────────┘    └──────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## MCP Tools Exposed

### `route_request`
Analyzes user request and routes to correct agent based on HANDOFF-PROTOCOL.md boundary table.

Input: `{ "request": string, "context": object }`
Output: `{ "agent": "ce7" | "coding", "reason": string }`

### `ce7_decide`
Sends request to CE7 agent, returns decision + Implementation Input Package.

Input: `{ "request": string, "constraints": object }`
Output: `{ "decision": string, "input_package": YAML, "adr_id": string }`

### `coding_implement`
Sends Implementation Input Package to Coding agent, returns code + Self-Review Block.

Input: `{ "input_package": YAML, "additional_context": string }`
Output: `{ "code": string, "self_review_block": YAML, "residual_risks": string[] }`

### `handoff_state`
Get/set handoff state for an ADR.

Input: `{ "adr_id": string, "action": "get" | "set", "data": object }`
Output: `{ "state": object }`

### `re_engage_ce7`
Triggered when Coding detects a re-engagement signal (§5 of HANDOFF-PROTOCOL.md).

Input: `{ "adr_id": string, "signal": string, "context": string }`
Output: `{ "ce7_response": string, "updated_package": YAML }`

## Handoff State Schema

```json
{
  "adr_id": "ADR-2026-04-payment-idempotency",
  "status": "ce7_decided | coding_in_progress | coding_done | ce7_reviewing",
  "input_package": { ... },
  "return_package": { ... },
  "re_engagements": [
    { "signal": "...", "ce7_response": "...", "timestamp": "..." }
  ],
  "conversation_log": [
    { "agent": "ce7", "turn": 1, "summary": "..." },
    { "agent": "coding", "turn": 2, "summary": "..." }
  ]
}
```

## Routing Rules (from HANDOFF-PROTOCOL.md §2)

```python
CE7_SIGNALS = [
    "affects > 1 service",
    "vendor selection",
    "SLO/SLI definition",
    "public API versioning",
    "multi-tenant isolation",
    "resilience pattern selection",
    "caching strategy",
    "cannot be reversed in single deploy",
]

def route(request: str) -> str:
    if any(signal in request.lower() for signal in CE7_SIGNALS):
        return "ce7"
    return "coding"
```

## Implementation Plan

1. **Phase 1**: MCP server skeleton with `route_request` tool only
2. **Phase 2**: Add `ce7_decide` and `coding_implement` with state management
3. **Phase 3**: Add `re_engage_ce7` and full conversation tracking
4. **Phase 4**: Add token tracking and cost metrics

## File Structure

```
orchestrator/
├── server.py              # MCP server entry point
├── router.py              # Boundary-based routing logic
├── state.py               # Handoff state management
├── agents/
│   ├── ce7.py             # CE7 agent interface
│   └── coding.py          # Coding agent interface
├── schemas/
│   ├── input_package.py   # Pydantic model for CE7 → Coding
│   └── return_package.py  # Pydantic model for Coding → CE7
└── tests/
    ├── test_router.py
    └── test_state.py
```

## Token Tracking Integration (P2)

Every tool call records:
- `input_tokens`: tokens sent to the agent
- `output_tokens`: tokens received from the agent
- `total_cost`: estimated cost based on model pricing
- `latency_ms`: wall time

Exposed via `get_metrics` tool for eval harness consumption.
