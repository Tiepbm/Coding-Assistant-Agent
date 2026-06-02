#!/usr/bin/env bash
# test-mcp.sh — kiểm tra toàn bộ MCP stack (dùng được trong dev repo lẫn bundle).
#
# Usage (từ root của repo hoặc bundle):
#   bash test-mcp.sh            # chạy cả 4 tầng
#   bash test-mcp.sh quick      # chỉ selftest (không cần mcp package)
#   bash test-mcp.sh unit       # chỉ pytest
#   bash test-mcp.sh json       # output JSON thô từ CLI
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-all}"
PASS=0; FAIL=0

if [[ -z "${MEMORY_AGENT:-}" ]]; then
  if [[ -f "$ROOT/.vscode/mcp.json" ]]; then
    MEMORY_AGENT_FROM_CONFIG=$(python3 - "$ROOT/.vscode/mcp.json" <<'PY' 2>/dev/null || true
import json
import sys

cfg = json.load(open(sys.argv[1]))
for server in cfg.get("servers", {}).values():
    agent = server.get("env", {}).get("MEMORY_AGENT")
    if agent:
        print(agent)
        break
PY
)
  fi
  if [[ -n "${MEMORY_AGENT_FROM_CONFIG:-}" ]]; then
    export MEMORY_AGENT="$MEMORY_AGENT_FROM_CONFIG"
  else
    case "$(basename "$ROOT")" in
      ce7|software-engineering-agent) export MEMORY_AGENT="ce7" ;;
      dual)                           export MEMORY_AGENT="dual" ;;
      *)                              export MEMORY_AGENT="coding" ;;
    esac
  fi
fi

# Tìm MCP server dir (dev repo: mcp-memory/ ở root; bundle: .github/mcp-memory/)
if   [[ -d "$ROOT/mcp-memory"         ]]; then MCP_MEM="$ROOT/mcp-memory";        MCP_SKL="$ROOT/mcp-skills";        MCP_GRD="$ROOT/mcp-grounding"
elif [[ -d "$ROOT/.github/mcp-memory" ]]; then MCP_MEM="$ROOT/.github/mcp-memory"; MCP_SKL="$ROOT/.github/mcp-skills"; MCP_GRD="$ROOT/.github/mcp-grounding"
else echo -e "${RED}ERROR: không tìm thấy mcp-memory/ (chạy từ root của repo hoặc bundle)${NC}"; exit 1
fi

ok()   { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
info() { echo -e "  ${YELLOW}·${NC} $1"; }

echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo -e "${BOLD}  MCP Stack Test — $(basename "$ROOT")${NC}"
echo -e "${BOLD}═══════════════════════════════════════${NC}"
echo ""

# ── Tầng 0: Python & package ──────────────────────────────────────────────
if [[ "$MODE" == "all" || "$MODE" == "quick" ]]; then
  echo -e "${BOLD}[0] Môi trường${NC}"
  PY=$(python3 --version 2>&1) && ok "$PY" || fail "python3 không tìm thấy"

  if python3 -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    MCP_VER=$(python3 -c "import importlib.metadata; print(importlib.metadata.version('mcp'))" 2>/dev/null || echo "?")
    ok "mcp package v$MCP_VER — MCP server sẽ chạy đầy đủ"
    HAS_MCP=1
  else
    info "mcp package chưa cài — server không start được, nhưng CLI + selftest vẫn chạy"
    info "Cài: pip install -r $MCP_MEM/requirements.txt"
    HAS_MCP=0
  fi
  echo ""
fi

# ── Tầng 1: --selftest (không cần mcp package) ───────────────────────────
if [[ "$MODE" == "all" || "$MODE" == "quick" ]]; then
  echo -e "${BOLD}[1] Selftest (--selftest flag)${NC}"

  run_selftest() {
    local name="$1" dir="$2"
    out=$(python3 "$dir/server.py" --selftest 2>&1)
    if echo "$out" | grep -qE "Traceback|Error:|Exception:|SyntaxError|TypeError|ValueError|ModuleNotFoundError"; then
      fail "$name: $out"
    else
      ok "$name"
      echo "$out" | sed 's/^/       /'
    fi
  }

  run_selftest "agent-memory   " "$MCP_MEM"
  run_selftest "agent-skills   " "$MCP_SKL"
  run_selftest "agent-grounding" "$MCP_GRD"
  echo ""
fi

# ── Tầng 2: CLI tools (stdlib only, không cần mcp) ───────────────────────
if [[ "$MODE" == "all" || "$MODE" == "json" ]]; then
  echo -e "${BOLD}[2] CLI tools (JSON output)${NC}"

  check_cli() {
    local label="$1"; shift
    out=$(python3 "$@" 2>&1) || true
    if [[ -z "$out" ]]; then
      fail "$label: no output"; return
    fi
    # Valid JSON?
    if python3 -c "import sys,json; json.loads(sys.argv[1])" "$out" 2>/dev/null; then
      ok "$label → JSON valid"
    elif echo "$out" | grep -qE '"ok"|"references"|"agent"|"patterns"|"chunks"'; then
      ok "$label"
    else
      fail "$label: $out"
    fi
    [[ "$MODE" == "json" ]] && echo "$out" | python3 -m json.tool 2>/dev/null || true
  }

  check_cli "memory stats  " "$MCP_MEM/memory_cli.py" stats
  check_cli "memory recall " "$MCP_MEM/memory_cli.py" recall --query "test idempotency"
  check_cli "skills stats  " "$MCP_SKL/skills_cli.py" stats
  check_cli "skills search " "$MCP_SKL/skills_cli.py" search --query "idempotency"
  check_cli "grounding val " "$MCP_GRD/grounding_cli.py" validate
  echo ""
fi

# ── Tầng 3: pytest (unit tests) ───────────────────────────────────────────
if [[ "$MODE" == "all" || "$MODE" == "unit" ]]; then
  echo -e "${BOLD}[3] Unit tests (pytest)${NC}"

  if ! command -v pytest &>/dev/null && ! python3 -m pytest --version &>/dev/null 2>&1; then
    info "pytest không tìm thấy — bỏ qua (cài: pip install pytest)"
  else
    run_pytest() {
      local name="$1" dir="$2"
      if ls "$dir"/test_*.py &>/dev/null 2>&1; then
        result=$(python3 -m pytest "$dir/" -q --tb=short 2>&1 | tail -3)
        if echo "$result" | grep -q "passed" && ! echo "$result" | grep -q "failed\|error"; then
          ok "$name: $result"
        else
          fail "$name: $result"
        fi
      else
        info "$name: không có test file"
      fi
    }
    run_pytest "memory   " "$MCP_MEM"
    run_pytest "skills   " "$MCP_SKL"
    run_pytest "grounding" "$MCP_GRD"
  fi
  echo ""
fi

# ── Tầng 4: MCP stdio handshake (cần mcp package) ────────────────────────
if [[ "$MODE" == "all" ]] && [[ "${HAS_MCP:-0}" == "1" ]]; then
  echo -e "${BOLD}[4] MCP stdio handshake (tools/list)${NC}"
  info "Dùng Python MCP client gửi tools/list → server phải trả về danh sách tool"

  stdio_test() {
    local name="$1" script="$2"
    local out status tools
    set +e
    out=$(python3 - "$script" <<'PY' 2>&1
import anyio
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    script = sys.argv[1]
    params = StdioServerParameters(command=sys.executable, args=[script])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            print("TOOLS:" + ", ".join(t.name for t in result.tools))


anyio.run(main)
PY
)
    status=$?
    set -e
    if [[ $status -eq 0 ]] && echo "$out" | grep -q '^TOOLS:'; then
      tools=$(echo "$out" | sed -n 's/^TOOLS://p' | tail -1)
      ok "$name tools: $tools"
    else
      fail "$name: không nhận được tools/list response"
      echo "$out" | sed 's/^/       /'
    fi
  }

  stdio_test "agent-memory   " "$MCP_MEM/server.py"
  stdio_test "agent-skills   " "$MCP_SKL/server.py"
  stdio_test "agent-grounding" "$MCP_GRD/server.py"
  echo ""
fi

# ── Tổng kết ──────────────────────────────────────────────────────────────
echo -e "${BOLD}═══════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL))
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}  PASS $PASS/$TOTAL${NC} — MCP stack hoạt động bình thường"
else
  echo -e "${RED}${BOLD}  FAIL $FAIL/$TOTAL${NC} (pass: $PASS)"
fi
echo -e "${BOLD}═══════════════════════════════════════${NC}"
[[ $FAIL -eq 0 ]]
