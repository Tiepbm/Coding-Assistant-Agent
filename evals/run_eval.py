#!/usr/bin/env python3
"""Coding Assistant eval runner.

Reads a JSONL benchmark and a JSONL responses file, scores each task per
`evals/rubric.md`, writes a JSON report, and exits non-zero if pass-rate is
below `--fail-under` or any `--critical-must-pass` task fails.

Usage:
    python evals/run_eval.py \\
        --benchmark evals/coding-benchmark.jsonl \\
        --responses runs/$RUN_ID/responses.jsonl \\
        --report   runs/$RUN_ID/report.json \\
        --fail-under 90 \\
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

# ---------------------------------------------------------------------------
# Rubric weights — keep in sync with evals/rubric.md
# ---------------------------------------------------------------------------
W_ROUTING = 20
W_INCLUSION = 30
W_EXCLUSION = 20
W_TEST = 15
W_COMPILES = 15
PASS_THRESHOLD = 75

# Heuristics for detecting a runnable test by language/framework.
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
    "yaml":       [],  # workflows often include test step explicitly
    "dockerfile": [],
    "sql":        [],
    "proto":      [],
}

CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)?\n(.*?)```", re.DOTALL)

LANG_ALIASES = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "yml": "yaml",
    "sh": "bash",
    "shell": "bash",
    "docker": "dockerfile",
}


@dataclass
class TaskResult:
    id: str
    score: int
    passed: bool
    routing_ok: bool
    missing_includes: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    has_test: bool = False
    compiles: bool = True
    syntax_checked: bool = False
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


def extract_code(response: str) -> str:
    """Return concatenated content of all fenced code blocks."""
    return "\n".join(body for _, body in CODE_BLOCK_RE.findall(response))


def extract_code_blocks(response: str) -> list[tuple[str, str]]:
    """Return normalized (language, code) tuples from fenced code blocks."""
    blocks: list[tuple[str, str]] = []
    for lang, body in CODE_BLOCK_RE.findall(response):
        normalized = LANG_ALIASES.get(lang.lower(), lang.lower())
        blocks.append((normalized, body))
    return blocks


def has_runnable_test(response: str, language: str) -> bool:
    code = extract_code(response)
    sigs = TEST_SIGNATURES.get(language.lower(), [])
    if not sigs:
        return True  # not enforced for non-code answers
    return any(re.search(p, code) for p in sigs)


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Run a syntax command and return (ok, diagnostic)."""
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
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
    """Best-effort syntax checks. Returns (checked, ok, diagnostic).

    Many agent answers contain partial snippets that are not standalone programs.
    For those languages, this function only checks when the block looks like a
    complete file and the local toolchain is available; otherwise it skips.
    """
    if language == "python":
        return check_python_syntax(code)
    if language == "json":
        return check_json_syntax(code)
    if language in {"javascript", "bash"}:
        tool = "node" if language == "javascript" else "bash"
        if not shutil.which(tool):
            return False, True, f"{tool} not installed; skipped syntax check"
        suffix = ".js" if language == "javascript" else ".sh"
        with TemporaryDirectory() as td:
            path = Path(td) / f"snippet{suffix}"
            path.write_text(code)
            cmd = [tool, "--check", str(path)] if language == "javascript" else [tool, "-n", str(path)]
            ok, diag = run_command(cmd)
            return True, ok, diag
    if language == "go":
        if "package " not in code or not shutil.which("gofmt"):
            return False, True, "go block is not a standalone file or gofmt missing; skipped syntax check"
        with TemporaryDirectory() as td:
            path = Path(td) / "snippet.go"
            path.write_text(code)
            ok, diag = run_command(["gofmt", "-w", str(path)])
            return True, ok, diag
    if language == "rust":
        if not shutil.which("rustfmt"):
            return False, True, "rustfmt not installed; skipped syntax check"
        with TemporaryDirectory() as td:
            path = Path(td) / "snippet.rs"
            path.write_text(code)
            ok, diag = run_command(["rustfmt", "--check", str(path)])
            return True, ok, diag
    return False, True, f"no local syntax checker configured for {language or 'unlabeled'}; skipped"


def syntax_check_response(response: str, expected_language: str) -> tuple[bool, bool, list[str]]:
    """Best-effort syntax validation for code blocks relevant to a task.

    Returns (checked_any, all_checked_ok, notes).
    """
    expected = LANG_ALIASES.get(expected_language.lower(), expected_language.lower())
    notes: list[str] = []
    checked_any = False
    all_ok = True

    for language, code in extract_code_blocks(response):
        # Avoid punishing explanatory YAML/JSON snippets in Java/Python answers.
        if language and expected and language != expected:
            continue
        checked, ok, diagnostic = check_external_syntax(language or expected, code)
        checked_any = checked_any or checked
        if diagnostic:
            notes.append(diagnostic)
        if checked and not ok:
            all_ok = False

    if not checked_any:
        notes.append("syntax check skipped: no standalone checkable code block/tool found")
    return checked_any, all_ok, notes


def score_task(task: dict[str, Any], response: dict[str, Any]) -> TaskResult:
    res = TaskResult(id=task["id"], score=0, passed=False, routing_ok=False)
    text = response.get("response", "") or ""
    code = extract_code(text)

    # Routing (20)
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

    # Inclusion (30) — proportional
    must_include = task.get("must_include", []) or []
    if must_include:
        hits = [s for s in must_include if s in text]
        res.missing_includes = [s for s in must_include if s not in text]
        res.score += int(W_INCLUSION * (len(hits) / len(must_include)))
    else:
        res.score += W_INCLUSION

    # Exclusion (20) — all-or-nothing
    must_not_include = task.get("must_not_include", []) or []
    res.forbidden_found = [s for s in must_not_include if s in code]
    if not res.forbidden_found:
        res.score += W_EXCLUSION

    # Test present (15)
    res.has_test = has_runnable_test(text, task.get("language", ""))
    if res.has_test:
        res.score += W_TEST

    # Compiles (15) — best-effort syntax check; skipped tools don't fail snippets.
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

    res.passed = res.score >= PASS_THRESHOLD and res.compiles
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--responses", type=Path, required=True)
    ap.add_argument("--report",    type=Path, required=True)
    ap.add_argument("--fail-under", type=float, default=90.0,
                    help="Minimum pass-rate %% required (default 90)")
    ap.add_argument("--critical-must-pass", default="",
                    help="Comma-separated task IDs that MUST pass (security/data-loss)")
    ap.add_argument("--dry-run", action="store_true", help="Validate JSONL shape only")
    args = ap.parse_args()

    tasks = load_jsonl(args.benchmark)
    if args.dry_run:
        print(f"OK: {len(tasks)} tasks parsed from {args.benchmark}")
        return 0

    responses_by_id = {r["id"]: r for r in load_jsonl(args.responses)}

    results: list[TaskResult] = []
    for task in tasks:
        resp = responses_by_id.get(task["id"], {"response": "", "packs_invoked": [], "references_invoked": []})
        results.append(score_task(task, resp))

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = (passed / total) * 100 if total else 0.0

    critical_ids = {s.strip() for s in args.critical_must_pass.split(",") if s.strip()}
    critical_failed = [r.id for r in results if r.id in critical_ids and not r.passed]

    report = {
        "summary": {
            "total": total, "passed": passed,
            "pass_rate_pct": round(pass_rate, 2),
            "fail_under_pct": args.fail_under,
            "critical_failed": critical_failed,
        },
        "tasks": [asdict(r) for r in results],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))

    print(f"Passed {passed}/{total} ({pass_rate:.1f}%)")
    if critical_failed:
        print(f"CRITICAL FAILURES: {critical_failed}", file=sys.stderr)

    if pass_rate < args.fail_under:
        print(f"FAIL: pass-rate {pass_rate:.1f}%% < required {args.fail_under}%%", file=sys.stderr)
        return 1
    if critical_failed:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

