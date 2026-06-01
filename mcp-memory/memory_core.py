"""Shared memory core for the dual-agent learning loop.

Pure-stdlib (sqlite3 only) so it can be used by:
- the MCP server (`server.py`),
- the CLI used by hooks (`memory_cli.py`),
- tests (`test_memory.py`).

Storage: local SQLite at $MEMORY_DB (default ~/.copilot-agent-memory/<agent>.db).
Privacy: stores summaries + metadata only — never prompt bodies, code, secrets, or PII.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

AGENT = os.environ.get("MEMORY_AGENT", "coding")

# Outcome → score used for pattern confidence.
OUTCOME_SCORES = {
    "accepted": 1.0,
    "edited": 0.6,
    "auto": 0.5,
    "unknown": 0.5,
    "repeated": 0.3,
    "rejected": 0.0,
}

# Bound recall output so it never blows the token budget.
RECALL_CHAR_BUDGET = 800  # ~200 tokens


def db_path() -> Path:
    env = os.environ.get("MEMORY_DB")
    if env:
        return Path(os.path.expanduser(env))
    return Path(os.path.expanduser(f"~/.copilot-agent-memory/{AGENT}.db"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp._fts_probe USING fts5(x);")
        conn.execute("DROP TABLE temp._fts_probe;")
        return True
    except sqlite3.OperationalError:
        return False


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            agent           TEXT NOT NULL,
            prompt_summary  TEXT NOT NULL,
            domain          TEXT,
            risk_class      TEXT,
            packs           TEXT NOT NULL,   -- JSON array
            refs            TEXT NOT NULL,   -- JSON array
            outcome         TEXT NOT NULL,   -- accepted|edited|auto|repeated|rejected|unknown
            source          TEXT NOT NULL DEFAULT 'hook'  -- hook|mcp|manual
        );

        CREATE TABLE IF NOT EXISTS patterns (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            signature    TEXT NOT NULL UNIQUE,  -- domain|sorted(packs)
            domain       TEXT,
            packs        TEXT NOT NULL,
            frequency    INTEGER NOT NULL DEFAULT 0,
            score_sum    REAL NOT NULL DEFAULT 0,
            confidence   REAL NOT NULL DEFAULT 0.5,
            last_seen    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS corrections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            prompt_summary  TEXT NOT NULL,
            expected_packs  TEXT NOT NULL,
            actual_packs    TEXT NOT NULL,
            root_cause      TEXT NOT NULL,
            fixed           INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    if _has_fts5(conn):
        conn.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS interactions_fts
                USING fts5(prompt_summary, domain, packs, content='interactions', content_rowid='id');
            """
        )
    conn.commit()


def _fts_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='interactions_fts'"
    ).fetchone()
    return row is not None


def _signature(domain: str | None, packs: list[str]) -> str:
    return f"{(domain or 'general').lower()}|{'+'.join(sorted(p.lower() for p in packs))}"


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except json.JSONDecodeError:
            pass
        return [p.strip() for p in re.split(r"[,\s]+", value) if p.strip()]
    return [str(value)]


def record_outcome(
    conn: sqlite3.Connection,
    *,
    prompt_summary: str,
    packs,
    refs=None,
    domain: str | None = None,
    risk_class: str | None = None,
    outcome: str = "auto",
    source: str = "hook",
) -> int:
    packs_l = _as_list(packs)
    refs_l = _as_list(refs)
    outcome = outcome if outcome in OUTCOME_SCORES else "unknown"
    ts = _now()

    cur = conn.execute(
        """INSERT INTO interactions
           (timestamp, agent, prompt_summary, domain, risk_class, packs, refs, outcome, source)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            ts,
            AGENT,
            prompt_summary[:300],
            domain,
            risk_class,
            json.dumps(packs_l, ensure_ascii=False),
            json.dumps(refs_l, ensure_ascii=False),
            outcome,
            source,
        ),
    )
    rowid = cur.lastrowid
    if _fts_available(conn):
        conn.execute(
            "INSERT INTO interactions_fts(rowid, prompt_summary, domain, packs) VALUES (?,?,?,?)",
            (rowid, prompt_summary[:300], domain or "", " ".join(packs_l)),
        )
    _bump_pattern(conn, domain, packs_l, OUTCOME_SCORES[outcome], ts)
    conn.commit()
    return rowid


def _bump_pattern(conn, domain, packs, score, ts) -> None:
    if not packs:
        return
    sig = _signature(domain, packs)
    row = conn.execute("SELECT id, frequency, score_sum FROM patterns WHERE signature=?", (sig,)).fetchone()
    if row:
        freq = row["frequency"] + 1
        score_sum = row["score_sum"] + score
        conn.execute(
            "UPDATE patterns SET frequency=?, score_sum=?, confidence=?, last_seen=? WHERE id=?",
            (freq, score_sum, round(score_sum / freq, 3), ts, row["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO patterns (signature, domain, packs, frequency, score_sum, confidence, last_seen)
               VALUES (?,?,?,?,?,?,?)""",
            (sig, domain, json.dumps(sorted(packs), ensure_ascii=False), 1, score, round(score, 3), ts),
        )


def record_correction(
    conn: sqlite3.Connection,
    *,
    prompt_summary: str,
    expected_packs,
    actual_packs,
    root_cause: str,
) -> int:
    expected = _as_list(expected_packs)
    actual = _as_list(actual_packs)
    cur = conn.execute(
        """INSERT INTO corrections (timestamp, prompt_summary, expected_packs, actual_packs, root_cause)
           VALUES (?,?,?,?,?)""",
        (
            _now(),
            prompt_summary[:300],
            json.dumps(expected, ensure_ascii=False),
            json.dumps(actual, ensure_ascii=False),
            root_cause[:300],
        ),
    )
    # Penalize the wrong pattern's confidence.
    if actual:
        sig = _signature(None, actual)
        conn.execute(
            "UPDATE patterns SET confidence=MAX(0.0, confidence-0.2) WHERE signature LIKE ?",
            (f"%|{'+'.join(sorted(p.lower() for p in actual))}",),
        )
    conn.commit()
    return cur.lastrowid


def _tokenize(query: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", query.lower()) if len(t) > 2]


def recall(conn: sqlite3.Connection, query: str, k: int = 3) -> dict:
    """Return bounded patterns + corrections relevant to the query."""
    patterns: list[dict] = []
    seen = set()

    if _fts_available(conn):
        terms = _tokenize(query)
        if terms:
            match = " OR ".join(terms)
            try:
                rows = conn.execute(
                    "SELECT rowid FROM interactions_fts WHERE interactions_fts MATCH ? LIMIT 25",
                    (match,),
                ).fetchall()
                ids = [r["rowid"] for r in rows]
                if ids:
                    placeholders = ",".join("?" * len(ids))
                    irows = conn.execute(
                        f"SELECT domain, packs FROM interactions WHERE id IN ({placeholders})", ids
                    ).fetchall()
                    for ir in irows:
                        sig = _signature(ir["domain"], _as_list(ir["packs"]))
                        if sig not in seen:
                            seen.add(sig)
            except sqlite3.OperationalError:
                pass

    # Rank patterns by (matched signatures first) then confidence*frequency.
    prows = conn.execute(
        "SELECT domain, packs, frequency, confidence FROM patterns ORDER BY confidence*frequency DESC LIMIT 50"
    ).fetchall()
    terms = set(_tokenize(query))
    for pr in prows:
        sig = _signature(pr["domain"], _as_list(pr["packs"]))
        pack_terms = set(_tokenize(" ".join(_as_list(pr["packs"])) + " " + (pr["domain"] or "")))
        relevant = (sig in seen) or bool(terms & pack_terms)
        if relevant:
            patterns.append(
                {
                    "domain": pr["domain"] or "general",
                    "packs": _as_list(pr["packs"]),
                    "frequency": pr["frequency"],
                    "confidence": pr["confidence"],
                }
            )
        if len(patterns) >= k:
            break

    corr_rows = conn.execute(
        "SELECT expected_packs, actual_packs, root_cause FROM corrections ORDER BY id DESC LIMIT 20"
    ).fetchall()
    corrections = []
    for cr in corr_rows:
        actual_terms = set(_tokenize(" ".join(_as_list(cr["actual_packs"])) + " " + cr["root_cause"]))
        if terms & actual_terms:
            corrections.append(
                {
                    "expected": _as_list(cr["expected_packs"]),
                    "avoid": _as_list(cr["actual_packs"]),
                    "why": cr["root_cause"],
                }
            )
        if len(corrections) >= 2:
            break

    result = {"patterns": patterns[:k], "corrections": corrections}
    return _bound(result)


def _bound(result: dict) -> dict:
    """Trim recall payload to the char budget."""
    blob = json.dumps(result, ensure_ascii=False)
    while len(blob) > RECALL_CHAR_BUDGET and result["patterns"]:
        result["patterns"].pop()
        blob = json.dumps(result, ensure_ascii=False)
    while len(blob) > RECALL_CHAR_BUDGET and result["corrections"]:
        result["corrections"].pop()
        blob = json.dumps(result, ensure_ascii=False)
    return result


def synthesize(conn: sqlite3.Connection) -> dict:
    """Recompute confidence from interactions (idempotent). Returns summary."""
    conn.execute("DELETE FROM patterns")
    rows = conn.execute("SELECT domain, packs, outcome FROM interactions").fetchall()
    for r in rows:
        packs = _as_list(r["packs"])
        score = OUTCOME_SCORES.get(r["outcome"], 0.5)
        _bump_pattern(conn, r["domain"], packs, score, _now())
    conn.commit()
    n = conn.execute("SELECT COUNT(*) c FROM patterns").fetchone()["c"]
    return {"patterns": n}


def get_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) c FROM interactions").fetchone()["c"]
    corr = conn.execute("SELECT COUNT(*) c FROM corrections").fetchone()["c"]
    # Accuracy proxy: 1 - corrections/total, clamped.
    accuracy = round(max(0.0, 1.0 - (corr / total)), 3) if total else None
    avg_score_row = conn.execute(
        "SELECT AVG(confidence) a FROM patterns"
    ).fetchone()
    quality = round(avg_score_row["a"], 3) if avg_score_row["a"] is not None else None
    top = conn.execute(
        "SELECT packs, frequency, confidence FROM patterns ORDER BY frequency DESC LIMIT 5"
    ).fetchall()
    return {
        "agent": AGENT,
        "interactions": total,
        "corrections": corr,
        "routing_accuracy_proxy": accuracy,
        "avg_pattern_confidence": quality,
        "top_patterns": [
            {"packs": _as_list(t["packs"]), "frequency": t["frequency"], "confidence": t["confidence"]}
            for t in top
        ],
    }


def export_patterns(conn: sqlite3.Connection, out_path: Path) -> int:
    rows = conn.execute(
        "SELECT domain, packs, frequency, confidence FROM patterns "
        "WHERE frequency >= 2 ORDER BY confidence*frequency DESC LIMIT 40"
    ).fetchall()
    lines = [
        "# Learned Patterns (auto-exported from memory)",
        "",
        f"> Generated {(_now())} from {AGENT} memory. Maintainer-reviewed before promotion to pack guidance.",
        "",
    ]
    for r in rows:
        packs = " + ".join(_as_list(r["packs"]))
        lines.append(
            f"- **{r['domain'] or 'general'}** → `{packs}` "
            f"(seen {r['frequency']}x, confidence {r['confidence']:.2f})"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


def report_accuracy(conn: sqlite3.Connection, out_path: Path) -> dict:
    stats = get_stats(conn)
    entry = {"timestamp": _now(), **stats}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


# --- P3: promotion loop (DB → learned-patterns.md, human-reviewed) ---

import re as _re  # local alias to keep the public API tidy

_PROMO_MARKER = _re.compile(r"<!--\s*promo:(.*?)\s*-->")


def _corr_signature(expected: list[str], actual: list[str]) -> str:
    e = "+".join(sorted(p.lower() for p in expected))
    a = "+".join(sorted(p.lower() for p in actual))
    return f"corr|{a}=>{e}"


def promotion_candidates(
    conn: sqlite3.Connection,
    *,
    min_freq: int = 3,
    min_conf: float = 0.7,
    min_corr: int = 2,
) -> dict:
    """Stable patterns + recurring corrections worth promoting into pack guidance."""
    patterns = []
    for row in conn.execute(
        "SELECT domain, packs, frequency, confidence FROM patterns "
        "WHERE frequency >= ? AND confidence >= ? ORDER BY confidence*frequency DESC",
        (min_freq, min_conf),
    ):
        packs = _as_list(row["packs"])
        if not packs:
            continue
        patterns.append(
            {
                "signature": _signature(row["domain"], packs),
                "domain": row["domain"] or "general",
                "packs": packs,
                "frequency": row["frequency"],
                "confidence": round(row["confidence"], 3),
            }
        )

    corr_counts: dict[str, dict] = {}
    for row in conn.execute("SELECT expected_packs, actual_packs, root_cause FROM corrections"):
        exp = _as_list(row["expected_packs"])
        act = _as_list(row["actual_packs"])
        if not (exp and act):
            continue
        sig = _corr_signature(exp, act)
        entry = corr_counts.setdefault(
            sig, {"signature": sig, "expected": exp, "avoid": act, "why": row["root_cause"], "count": 0}
        )
        entry["count"] += 1
    corrections = [c for c in corr_counts.values() if c["count"] >= min_corr]
    corrections.sort(key=lambda x: -x["count"])
    return {"patterns": patterns, "corrections": corrections}


def render_promotion_md(candidates: dict, date: str | None = None) -> tuple[str, list[str]]:
    """Render PROPOSED markdown block + the list of signatures it covers."""
    date = date or _now()[:10]
    sigs: list[str] = []
    lines = [
        f"## PROPOSED (auto {date}) — review before promoting",
        "",
        "> Auto-derived from runtime memory. A maintainer must verify, then move stable items into",
        "> the curated section above or into pack `When NOT to Use` / Tie-Break rules, and delete the rest.",
        "",
    ]
    if candidates["patterns"]:
        lines.append("### Routing patterns")
        for p in candidates["patterns"]:
            packs = " + ".join(f"`{x}`" for x in p["packs"])
            lines.append(
                f"- **{p['domain']}** → {packs} "
                f"(seen {p['frequency']}x, confidence {p['confidence']:.2f}) "
                f"<!-- promo:{p['signature']} -->"
            )
            sigs.append(p["signature"])
        lines.append("")
    if candidates["corrections"]:
        lines.append("### Recurring routing corrections")
        for c in candidates["corrections"]:
            avoid = " + ".join(f"`{x}`" for x in c["avoid"])
            expected = " + ".join(f"`{x}`" for x in c["expected"])
            why = (c["why"] or "").strip()
            lines.append(
                f"- Do NOT route to {avoid}; use {expected} "
                f"(missed {c['count']}x — {why}) <!-- promo:{c['signature']} -->"
            )
            sigs.append(c["signature"])
        lines.append("")
    return "\n".join(lines), sigs


def promote_to_file(
    conn: sqlite3.Connection,
    out_path: Path,
    *,
    min_freq: int = 3,
    min_conf: float = 0.7,
    min_corr: int = 2,
) -> dict:
    """Append new (deduped) promotion candidates to learned-patterns.md. Idempotent."""
    candidates = promotion_candidates(conn, min_freq=min_freq, min_conf=min_conf, min_corr=min_corr)

    existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    existing_sigs = set(_PROMO_MARKER.findall(existing))

    fresh = {
        "patterns": [p for p in candidates["patterns"] if p["signature"] not in existing_sigs],
        "corrections": [c for c in candidates["corrections"] if c["signature"] not in existing_sigs],
    }
    n_new = len(fresh["patterns"]) + len(fresh["corrections"])
    if n_new == 0:
        return {"appended": 0, "patterns": 0, "corrections": 0}

    block, _sigs = render_promotion_md(fresh)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(f"{prefix}\n{block}\n")
    return {"appended": n_new, "patterns": len(fresh["patterns"]), "corrections": len(fresh["corrections"])}


