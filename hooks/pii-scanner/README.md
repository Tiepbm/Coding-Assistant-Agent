# PII Scanner

`preToolUse` hook that blocks likely real PII before it is written to code, logs, fixtures, or docs.

## Detects

- Vietnamese CMND/CCCD-like IDs: `9` or `12` digits.
- Vietnamese mobile phones: `03/05/07/08/09` + 8 digits.
- Personal email providers: Gmail/Yahoo/Outlook/Hotmail.
- Bank-account-like numbers when near account keywords.
- Insurance policy/claim numbers: `HD########`, `BT########`.

## Allowlist

Obvious placeholders are allowed: `user@example.com`, `0901234xxx`, `HD00000000`, `BT00000000`, `placeholder`, `dummy`, `fake`, `fixture`, `test data`.

## Environment

- `PII_MODE=block|warn` default `block`.
- `SKIP_PII_SCAN=true`.
- `PII_LOG_DIR=logs/copilot/pii-scanner`.

