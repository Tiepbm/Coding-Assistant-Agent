---
description: 'Shared conventions for all Coding Assistant pack SKILL.md files. Maintainer-only; NOT loaded at runtime.'
applyTo: 'skills/**/SKILL.md'
---
# Pack Conventions

## Pack Structure (REQUIRED)

Every pack SKILL.md must have these sections in order:
1. Frontmatter (name, description starting with "Use when")
2. When to Use (3-6 concrete triggers)
3. When NOT to Use (2-4 anti-triggers pointing to neighbor packs)
4. Pack Reference Map (table: Reference | Use when — distinct triggers per row)
5. Cross-Pack Handoffs (3-6 bullets: → pack for concern)

## Code Output Style

- BAD/GOOD pattern pairs with 1-line reasoning.
- Include imports, types, error handling.
- Inline comments only for non-obvious decisions.
- Always include a test alongside implementation code.
- Use the project's existing style when visible.

## Token Efficiency

- Pack = routing layer. References = code patterns + examples.
- Do not paste large code blocks in pack SKILL.md — keep in references.
- If > 3 references seem necessary, name the primary one and justify extras.

## Quality Gates

- Code compiles/runs without modification.
- Tests are executable (not pseudocode).
- Security patterns applied by default.
- Error handling included (not just happy path).
