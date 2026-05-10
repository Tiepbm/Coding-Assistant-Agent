#!/usr/bin/env bash
# Attest HANDOFF-PROTOCOL.md or the active input-package.yaml with SHA-256.

set -euo pipefail

hash_file() {
  local target="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$target" | awk '{print $1}'
  else
    shasum -a 256 "$target" | awk '{print $1}'
  fi
}

resolve_target() {
  if [[ -n "${1:-}" ]]; then
    printf '%s\n' "$1"
    return
  fi
  if [[ -f .handoffs/.active ]]; then
    local adr
    adr="$(tr -d '\r\n' < .handoffs/.active)"
    if [[ -n "$adr" && -f ".handoffs/$adr/input-package.yaml" ]]; then
      printf '%s\n' ".handoffs/$adr/input-package.yaml"
      return
    fi
  fi
  printf '%s\n' "HANDOFF-PROTOCOL.md"
}

target="$(resolve_target "${1:-}")"
if [[ ! -f "$target" ]]; then
  echo "[dual-agent-attest] File not found: $target" >&2
  exit 1
fi

hash="$(hash_file "$target")"
if [[ "$target" == .handoffs/*/input-package.yaml ]]; then
  out="$(dirname "$target")/.attestation"
else
  mkdir -p .handoffs
  out=".handoffs/.protocol-attestation"
fi
printf '%s\n' "$hash" > "$out"
echo "[dual-agent-attest] Attested $target -> ${hash:0:12}... ($out)"

