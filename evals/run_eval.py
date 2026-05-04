#!/usr/bin/env python3
"""Coding Assistant eval runner — v2.

v2 adds (per `docs/agent-runtime-evaluation.md`):
  - tier filter (regression | capability | holdout) sourced from `evals/eval-tiers.md`
  - transcript metrics: n_turns, n_toolcalls, tokens_total, latency_ms
  - per-task token_budget grader
  - trajectory edit-distance grader (expected_trajectory vs actual sequence)
  - guardrail-fired grader (expected_guardrails)
  - keeps v1 routing/inclusion/exclusion/test/compiles graders (lower weights)

Backwards compatible: tasks without new fields are graded as before.

Usage:
    python evals/run_eval.py \\
        --benchmark evals/coding-benchmark.jsonl \\
        --responses runs/$RUN_ID/responses.jsonl \\
        --report   runs/$RUN_ID/report.json \\
        --tier regression \\
        --tiers-config evals/eval-tiers.md \\
        --fail-under 95 \\
        --critical-must-pass code-024,code-001,code-011,code-017,code-018
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

# Weights — keep in sync with evals/rubric.md and docs/agent-runtime-evaluation.md
W_ROUTING = 15
W_INCLUSION = 25
W_EXCLUSION = 15
W_TEST = 10
W_COMPILES = 10
W_TRAJECTORY = 10
W_TOKEN_BUDGET = 10
W_GUARDRAILS = 5
PASS_THRESHOLD = 75

TEST_SIGNATURES: dict[str, list[str]] = {
    "java":       [r"@Test\b", r"assertThat\(", r"@SpringBootTest"],
    "kotlin":     [r"@Test\b", r"runTest\s*\{", r"coEvery", r"WebTestClient"],
    "csharp":     [r"\[Fact\]", r"\[Theory\]", r"Assert\.", r"WebApplicationFactory"],
    "typescript": [r"\b(test|it|describe)\s*\(", r"expect\("],
    "javascript": [r"\b(test|it|describe)\s*\(", r"expect\("],
    "python":     [r"\bdef test_", r"@pytest\.", r"assert\b"],
    "go":         [r"func Test\w+\(t \*testing\.T\)", r"t\.(Run|Fatal|Errorf|Helper)"],
    "rust":       [r"#\[(tokio::)?test\]", r"assert(_eq|_ne)?!"],
    "dart":       [r"\btestWidgets\(", r"\btest\(", r"\bexpect\("],
    "swift":      [r"class \w+\s*:\s*XCTestCase", r"func test\w+\(\)"],
    "yaml":       [],
    "dockerfile": [],
    "sql":        [],
    "proto":      [],
}

CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)?\n(.*?)```", re.DOTALL)
LANG_ALIASES = {
    "py": "python", "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript", "yml": "yaml",
    "sh": "bash", "shell": "bash", "docker": "dockerfile",
}

TIER_BLOCK_RE = re.compile(
    r"^- \*\*(?P<tier>regression|capability|holdout)\*\*[^\n]*?:?\s*(?P<ids>[^\n]+)$",
    re.MULTILINE,
)
TIER_RANGE_RE = re.compile(r"`(?P<a>[\w-]+)`\.\.`(?P<b>[\w-]+)`")
TIER_ID_RE = re.compile(r"`(?P<id>[\w-]+)`")


@dataclass
class TaskResult:
    id: str
    tier: str
    score: int
    passed: bool
    routing_ok: bool
    missing_includes: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    has_test: bool = False
    compiles: bool = True
    syntax_checked: bool = False
    trajectory_distance: int | None = None
    token_budget_ok: bool | None = None
    tokens_total: int | None = None
    guardrails_ok: bool | None = None
    n_turns: int | None = None
    n_toolcalls: int | None = None
    latency_ms: int | None = None
    notes: list[str] = field(default_factory=list)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"{path}:{i}: invalid JSON — {e}")
    return out


def parse_tier_config(path: Path, benchmark_stem: str) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text()
    needle = f"`{benchmark_stem}.jsonl`"
    idx = text.find(needle)
    if idx == -1:
        return {}
    end = text.find("\n### ", idx + 1)
    section = text[idx : end if end != -1 else len(text)]
    mapping: dict[str, str] = {}
    for m in TIER_BLOCK_RE.finditer(section):
        tier = m.group("tier")
        ids_str = m.group("ids")
        for r in TIER_RANGE_RE.finditer(ids_str):
            a, b = r.group("a"), r.group("b")
            pa = re.match(r"([A-Za-z-]+)(\d+)", a)
            pb = re.match(r"([A-Za-z-]+)(\d+)", b)
            if pa and pb and pa.group(1) == pb.group(1):
                width = len(pa.group(2))
                for n in range(int(pa.group(2)), int(pb.group(2)) + 1):
                    mapping[f"{pa.group(1)}{str(n).zfill(width)}"] = tier
        for s in TIER_ID_RE.finditer(ids_str):
            mapping[s.group("id")] = tier
    return mapping


def extract_code(response: str) -> str:
    return "\n".join(body for _, body in CODE_BLOCK_RE.findall(response))


def extract_code_blocks(response: str) -> list[tuple[str, str]]:
    return [(LANG_ALIASES.get(lang.lower(), lang.lower()), body)
            for lang, body in CODE_BLOCK_RE.findall(response)]


def has_runnable_test(response: str, language: str) -> bool:
    code = extract_code(response)
    sigs = TEST_SIGNATURES.get(language.lower(), [])
    if not sigs:
        return True
    return any(re.search(p, code) for p in sigs)


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    try:
        completed = subprocess.run(cmd, cwd=cwd, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=10, check=False)
    except subprocess.TimeoutExpired:
        return False, f"syntax check timed out: {' '.join(cmd)}"
    output = (completed.stderr or completed.stdout).strip()
    return completed.returncode == 0, output[:500]


def check_python_syntax(code: str) -> tuple[bool, bool, str]:
    try:
        ast.parse(code)
        return True, True, ""
    except SyntaxError as e:
        return True, False, f"python syntax error: {e}"


def check_json_syntax(code: str) -> tuple[bool, bool, str]:
    try:
        json.loads(code)
        return True, True, ""
    except json.JSONDecodeError as e:
        return True, False, f"json syntax error: {e}"


def check_external_syntax(language: str, code: str) -> tuple[bool, bool, str]:
    if language == "python":
        return check_python_syntax(code)
    if language == "json":
        return check_json_syntax(code)
    if language in {"javascript", "bash"}:
        tool = "node" if language == "javascript" else "bash"
        if not shutil.which(tool):
            return False, True, f"{tool} not installed; skipped"
        suffix = ".js" if language == "javascript" else ".sh"
        with TemporaryDirectory() as td:
            path = Path(td) / f"snippet{suffix}"
            path.write_text(code)
            cmd = [tool, "--check", str(path)] if language == "javascript" else [tool, "-n", str(path)]
            ok, diag = run_command(cmd)
            return True, ok, diag
    if language == "go":
        if "package " not in code or not shutil.which("gofmt"):
            return False, True, "go block not standalone or gofmt missing; skipped"
        with TemporaryDirectory() as td:
            path = Path(td) / "snippet.go"
            path.write_text(code)
            ok, diag = run_command(["gofmt", "-w", str(path)])
            return True, ok, diag
    if language == "rust":
        if not shutil.which("rustfmt"):
            return False, True, "rustfmt not installed; skipped"
        with TemporaryDirectory() as td:
            path = Path(td) / "snippet.rs"
            path.write_text(code)
            ok, diag = run_command(["rustfmt", "--check", str(path)])
            return True, ok, diag
    return False, True, f"no local syntax checker for {language or 'unlabeled'}; skipped"


def syntax_check_response(response: str, expected_language: str) -> tuple[bool, bool, list[str]]:
    expected = LANG_ALIASES.get(expected_language.lower(), expected_language.lower())
    notes: list[str] = []
    checked_any = False
    all_ok = True
    for language, code in extract_code_blocks(response):
        if language and expected and language != expected:
            continue
        checked, ok, diagnostic = check_external_syntax(language or expected, code)
        checked_any = checked_any or checked
        if diagnostic:
            notes.append(diagnostic)
        if checked and not ok:
            all_ok = False
    if not checked_any:
        notes.append("syntax check skipped: no standalone checkable block")
    return checked_any, all_ok, notes


def levenshtein(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = prev[j - 1] if ca == cb else 1 + min(prev[j], cur[j - 1], prev[j - 1])
        prev = cur
    return prev[-1]


def grade_trajectory(expected: list[str], actual: list[str], tier: str) -> tuple[int, bool]:
    if not expected:
        return -1, True
    dist = levenshtein(expected, actual)
    threshold = 1 if tier == "regression" else 3
    return dist, dist <= threshold


def grade_token_budget(budget: int | None, used: int | None) -> tuple[bool | None, float]:
    if not budget or used is None:
        return None, 1.0
    if used <= budget:
        return True, 1.0
    return False, max(0.0, budget / used)


def grade_guardrails(expected: list[str], triggered: list[str]) -> bool | None:
    if not expected:
        return None
    expected_set = set(expected)
    triggered_set = set(triggered or [])
    return expected_set.issubset(triggered_set) and not (triggered_set - expected_set)


def score_task(task: dict[str, Any], response: dict[str, Any], tier: str) -> TaskResult:
    res = TaskResult(id=task["id"], tier=tier, score=0, passed=False, routing_ok=False)
    text = response.get("response", "") or ""
    code = extract_code(text)

    res.n_turns = response.get("n_turns")
    res.n_toolcalls = response.get("n_toolcalls")
    res.tokens_total = response.get("tokens_total")
    res.latency_ms = response.get("latency_ms")

    expected_pack = task["expected_pack"]
    expected_refs = set(task.get("expected_references", []))
    packs_invoked = set(response.get("packs_invoked", []))
    refs_invoked = set(response.get("references_invoked", []))
    if expected_pack in packs_invoked and expected_refs.issubset(refs_invoked):
        res.score += W_ROUTING
        res.routing_ok = True
    else:
        res.notes.append(
            f"routing miss: expected pack={expected_pack} refs={sorted(expected_refs)}, "
            f"got packs={sorted(packs_invoked)} refs={sorted(refs_invoked)}"
        )

    must_include = task.get("must_include") or []
    if must_include:
        hits = [s for s in must_include if s in text]
        res.missing_includes = [s for s in must_include if s not in text]
        res.score += int(W_INCLUSION * (len(hits) / len(must_include)))
    else:
        res.score += W_INCLUSION

    must_not_include = task.get("must_not_include") or []
    res.forbidden_found = [s for s in must_not_include if s in code]
    if not res.forbidden_found:
        res.score += W_EXCLUSION

    res.has_test = has_runnable_test(text, task.get("language", ""))
    if res.has_test:
        res.score += W_TEST

    if code.strip():
        checked, ok, notes = syntax_check_response(text, task.get("language", ""))
        res.syntax_checked = checked
        res.notes.extend(notes)
        res.compiles = ok
        if ok:
            res.score += W_COMPILES
    else:
        res.compiles = False
        res.notes.append("no code block found")

    expected_traj = task.get("expected_trajectory") or []
    actual_traj = response.get("trajectory") or list(response.get("packs_invoked", []))
    dist, traj_ok = grade_trajectory(expected_traj, actual_traj, tier)
    res.trajectory_distance = dist if dist >= 0 else None
    if not expected_traj or traj_ok:
        res.score += W_TRAJECTORY
    else:
        res.notes.append(f"trajectory edit-distance {dist} exceeds threshold")

    budget = task.get("token_budget")
    tok_ok, _ = grade_token_budget(budget, res.tokens_total)
    res.token_budget_ok = tok_ok
    if tok_ok is None or tok_ok:
        res.score += W_TOKEN_BUDGET
    else:
        res.notes.append(f"token budget exceeded: used {res.tokens_total} > budget {budget}")

    expected_guards = task.get("expected_guardrails") or []
    triggered = response.get("guardrails_triggered") or []
    g_ok = grade_guardrails(expected_guards, triggered)
    res.guardrails_ok = g_ok
    if g_ok is None or g_ok:
        res.score += W_GUARDRAILS
    else:
        res.notes.append(f"guardrail mismatch: expected {expected_guards} got {triggered}")

    res.passed = res.score >= PASS_THRESHOLD and res.compiles
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--responses", type=Path, required=True)
    ap.add_argument("--report",    type=Path, required=True)
    ap.add_argument("--fail-under", type=float, default=90.0)
    ap.add_argument("--critical-must-pass", default="")
    ap.add_argument("--tier", choices=["regression", "capability", "holdout", "all"], default="all")
    ap.add_argument("--tiers-config", type=Path, default=Path(__file__).parent / "eval-tiers.md")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tasks = load_jsonl(args.benchmark)
    tier_map = parse_tier_config(args.tiers_config, args.benchmark.stem)

    def task_tier(t: dict[str, Any]) -> str:
        return t.get("tier") or tier_map.get(t["id"], "regression")

    if args.tier != "all":
        tasks = [t for t in tasks if task_tier(t) == args.tier]
        if not tasks:
            sys.exit(f"No tasks for tier={args.tier} in {args.benchmark}")

    if args.dry_run:
        print(f"OK: {len(tasks)} tasks parsed (tier={args.tier}) from {args.benchmark}")
        return 0

    responses_by_id = {r["id"]: r for r in load_jsonl(args.responses)}
    results: list[TaskResult] = []
    for task in tasks:
        resp = responses_by_id.get(task["id"], {
            "response": "", "packs_invoked": [], "references_invoked": [],
        })
        results.append(score_task(task, resp, task_tier(task)))

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = (passed / total) * 100 if total else 0.0

    critical_ids = {s.strip() for s in args.critical_must_pass.split(",") if s.strip()}
    critical_failed = [r.id for r in results if r.id in critical_ids and not r.passed]

    def agg(field_name: str) -> dict[str, Any]:
        values = [getattr(r, field_name) for r in results if getattr(r, field_name) is not None]
        if not values:
            return {"count": 0}
        values.sort()
        return {
            "count": len(values),
            "p50": values[len(values) // 2],
            "p95": values[max(0, int(len(values) * 0.95) - 1)],
            "max": values[-1],
        }

    report = {
        "summary": {
            "tier": args.tier,
            "total": total, "passed": passed,
            "pass_rate_pct": round(pass_rate, 2),
            "fail_under_pct": args.fail_under,
            "critical_failed": critical_failed,
            "transcript": {
                "n_turns": agg("n_turns"),
                "n_toolcalls": agg("n_toolcalls"),
                "tokens_total": agg("tokens_total"),
                "latency_ms": agg("latency_ms"),
                "trajectory_distance": agg("trajectory_distance"),
            },
        },
        "tasks": [asdict(r) for r in results],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))

    print(f"[tier={args.tier}] Passed {passed}/{total} ({pass_rate:.1f}%)")
    if critical_failed:
        print(f"CRITICAL FAILURES: {critical_failed}", file=sys.stderr)

    if pass_rate < args.fail_under:
        print(f"FAIL: pass-rate {pass_rate:.1f}% < required {args.fail_under}%", file=sys.stderr)
        return 1
    if critical_failed:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

