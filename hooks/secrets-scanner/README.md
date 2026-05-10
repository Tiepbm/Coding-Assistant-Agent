# Secrets Scanner

`sessionEnd` hook that scans changed text files for likely credentials.

## Detects

AWS keys, GitHub PATs, private-key blocks, Slack/Stripe/npm tokens, JWTs, generic `api_key/secret/password/token`, DB connection strings, internal IP:port endpoints, and insurance partner key patterns.

## Environment

- `SCAN_MODE=warn|block` default `warn`.
- `SCAN_SCOPE=diff|staged` default `diff`.
- `SECRETS_SCAN_TARGETS="file1 file2"` for tests/manual scans.
- `SECRETS_ALLOWLIST="regex"`.
- `SKIP_SECRETS_SCAN=true`.

