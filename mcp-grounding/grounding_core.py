"""Grounding/verification core for the dual-agent system.

Pure-stdlib. Lets the agent self-verify before finalizing an answer:
- run_validator()  : run the repo's pack validator and return a bounded verdict.
- check_contract() : lint an OpenAPI / GraphQL SDL / proto / JSON-schema fragment.
- handoff_diff()   : compare HANDOFF-PROTOCOL.md against the sibling repo's copy.

All outputs are bounded so they never blow the token budget. Heuristic linting is honest:
it catches common structural mistakes, not full schema validation.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path

TAIL_LINES = 25
DIFF_LINES = 40


def _repo_root() -> Path:
    """Repo root inferred from this file (mcp-grounding/ is a sibling of scripts/, skills/)."""
    return Path(__file__).resolve().parent.parent


# --- run_validator ------------------------------------------------------------

def _find_validator(root: Path) -> Path | None:
    for name in ("scripts/validate_packs.py", "scripts/validate_hybrid_packs.py"):
        p = root / name
        if p.is_file():
            return p
    return None


def run_validator(root: str | None = None, timeout: int = 60) -> dict:
    # If a root is given explicitly, respect it exactly. Otherwise try env, cwd, then the
    # repo root inferred from this file — so the server works even if the IDE spawns it
    # from another cwd.
    if root is not None:
        candidates = [Path(root).resolve()]
    else:
        candidates = []
        env = os.environ.get("GROUNDING_ROOT")
        if env:
            candidates.append(Path(env).resolve())
        candidates.append(Path(".").resolve())
        candidates.append(_repo_root())

    base = None
    validator = None
    for c in candidates:
        v = _find_validator(c)
        if v:
            base, validator = c, v
            break
    if not validator:
        return {"ok": False, "found": False, "reason": "no validator script in scripts/"}
    try:
        proc = subprocess.run(
            [sys.executable, str(validator)],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "found": True, "validator": validator.name, "reason": "timeout"}
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-TAIL_LINES:])
    return {
        "ok": proc.returncode == 0,
        "found": True,
        "validator": validator.name,
        "exit_code": proc.returncode,
        "tail": tail,
    }


# --- check_contract -----------------------------------------------------------

def _detect_format(text: str) -> str:
    t = text.strip()
    low = t.lower()
    if re.search(r"^\s*(openapi|swagger)\s*:", t, re.MULTILINE) or '"openapi"' in low or '"swagger"' in low:
        return "openapi"
    if re.search(r'syntax\s*=\s*["\']proto[23]["\']', t) or re.search(r"^\s*message\s+\w+\s*\{", t, re.MULTILINE):
        return "proto"
    if re.search(r"\btype\s+(Query|Mutation|Subscription)\b", t) or re.search(r"^\s*schema\s*\{", t, re.MULTILINE) or re.search(r"^\s*type\s+\w+\s*\{", t, re.MULTILINE):
        return "graphql"
    if t.startswith("{") or t.startswith("["):
        return "json"
    return "unknown"


def _check_braces(text: str) -> list[str]:
    issues = []
    if text.count("{") != text.count("}"):
        issues.append(f"unbalanced braces: {text.count('{')} '{{' vs {text.count('}')} '}}'")
    if text.count("(") != text.count(")"):
        issues.append(f"unbalanced parens: {text.count('(')} '(' vs {text.count(')')} ')'")
    return issues


def _check_openapi(text: str) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    # Try real JSON parse first; YAML if available.
    parsed = None
    if text.strip().startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            errors.append(f"invalid JSON: {e}")
    else:
        try:
            import yaml  # type: ignore
            parsed = yaml.safe_load(text)
        except ImportError:
            parsed = None  # fall back to text heuristics
        except Exception as e:  # noqa: BLE001
            errors.append(f"invalid YAML: {e}")

    if isinstance(parsed, dict):
        if not (parsed.get("openapi") or parsed.get("swagger")):
            errors.append("missing 'openapi'/'swagger' version field")
        paths = parsed.get("paths")
        if not isinstance(paths, dict) or not paths:
            errors.append("missing or empty 'paths'")
        else:
            for route, ops in paths.items():
                if not str(route).startswith("/"):
                    warnings.append(f"path '{route}' should start with '/'")
                if isinstance(ops, dict):
                    for verb, op in ops.items():
                        if isinstance(op, dict):
                            if "responses" not in op:
                                errors.append(f"{verb.upper()} {route}: missing 'responses'")
                            if "operationId" not in op:
                                warnings.append(f"{verb.upper()} {route}: missing 'operationId'")
    else:
        # Text heuristics (no parser available).
        if not re.search(r"^\s*(openapi|swagger)\s*:", text, re.MULTILINE):
            errors.append("missing 'openapi:'/'swagger:' version line")
        if not re.search(r"^\s*paths\s*:", text, re.MULTILINE):
            errors.append("missing 'paths:' section")
        if not re.search(r"^\s*responses\s*:", text, re.MULTILINE):
            warnings.append("no 'responses:' found")
        if not re.search(r"operationId\s*:", text):
            warnings.append("no 'operationId' found")
    return errors, warnings


def _check_graphql(text: str) -> tuple[list[str], list[str]]:
    errors = _check_braces(text)
    warnings = []
    if not re.search(r"\btype\s+\w+", text) and not re.search(r"\bschema\s*\{", text):
        errors.append("no 'type' or 'schema' definition found")
    if not re.search(r"\btype\s+(Query|Mutation|Subscription)\b", text):
        warnings.append("no root type (Query/Mutation/Subscription) found")
    return errors, warnings


def _check_proto(text: str) -> tuple[list[str], list[str]]:
    errors = _check_braces(text)
    warnings = []
    if not re.search(r'syntax\s*=\s*["\']proto3["\']', text):
        warnings.append("missing `syntax = \"proto3\";` (proto2 or unspecified)")
    if not re.search(r"\b(message|service)\s+\w+", text):
        errors.append("no 'message' or 'service' defined")
    if re.search(r"\bservice\s+\w+", text) and not re.search(r"\brpc\s+\w+", text):
        warnings.append("service defined without any 'rpc' method")
    return errors, warnings


def _check_json(text: str) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"], []
    if isinstance(obj, dict):
        if "$schema" in obj or "properties" in obj or "type" in obj:
            if obj.get("type") == "object" and "properties" not in obj:
                warnings.append("object schema without 'properties'")
        else:
            warnings.append("looks like data, not a schema (no $schema/type/properties)")
    return errors, warnings


_CHECKERS = {
    "openapi": _check_openapi,
    "graphql": _check_graphql,
    "proto": _check_proto,
    "json": _check_json,
}


def check_contract(text: str, fmt: str = "auto") -> dict:
    if not text or not text.strip():
        return {"ok": False, "format": "unknown", "errors": ["empty contract"], "warnings": []}
    fmt = fmt if fmt in _CHECKERS else _detect_format(text)
    checker = _CHECKERS.get(fmt)
    if not checker:
        return {"ok": False, "format": "unknown", "errors": ["could not detect contract format"], "warnings": []}
    errors, warnings = checker(text)
    return {
        "ok": not errors,
        "format": fmt,
        "errors": errors[:20],
        "warnings": warnings[:20],
    }


# --- handoff_diff -------------------------------------------------------------

def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _guess_sibling(local: Path) -> Path | None:
    # .../coding-assistant-agent/HANDOFF-PROTOCOL.md <-> .../software-engineering-agent/HANDOFF-PROTOCOL.md
    parent = local.resolve().parent
    workspace = parent.parent
    for sibling in ("software-engineering-agent", "coding-assistant-agent"):
        cand = workspace / sibling / "HANDOFF-PROTOCOL.md"
        if cand.exists() and cand.resolve() != local.resolve():
            return cand
    return None


def handoff_diff(local_path: str | None = None, other_path: str | None = None) -> dict:
    local = Path(local_path or "HANDOFF-PROTOCOL.md")
    if not local.exists():
        # Fall back to the repo root inferred from this file (cwd-independent).
        alt = _repo_root() / "HANDOFF-PROTOCOL.md"
        if alt.exists():
            local = alt
    if not local.exists():
        return {"ok": False, "reason": f"local not found: {local}"}
    other_env = other_path or os.environ.get("HANDOFF_OTHER")
    other = Path(other_env) if other_env else _guess_sibling(local)
    if not other or not other.exists():
        return {"ok": False, "reason": "sibling HANDOFF-PROTOCOL.md not found", "local": str(local)}

    if _hash(local) == _hash(other):
        return {"ok": True, "identical": True, "local": str(local), "other": str(other)}

    diff = list(
        unified_diff(
            other.read_text(encoding="utf-8").splitlines(),
            local.read_text(encoding="utf-8").splitlines(),
            fromfile=str(other),
            tofile=str(local),
            lineterm="",
        )
    )
    return {
        "ok": False,
        "identical": False,
        "local": str(local),
        "other": str(other),
        "canonical_owner": "software-engineering-agent (CE7)",
        "diff": "\n".join(diff[:DIFF_LINES]),
        "fix": "cp software-engineering-agent/HANDOFF-PROTOCOL.md coding-assistant-agent/HANDOFF-PROTOCOL.md",
    }

