"""Skill-retrieval core for the dual-agent reference layer.

Pure-stdlib. Indexes `skills/**/references/*.md` by heading so the agent can pull only the
matched section instead of loading a whole 250-line reference file (big token saving).

Used by:
- the MCP server (`server.py`),
- the CLI / token eval (`skills_cli.py`),
- tests (`test_skills.py`).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Output budgets (chars). ~4 chars/token → ~600 tokens for a search response.
SEARCH_CHAR_BUDGET = 2400
PER_CHUNK_CHARS = 900
LIST_CHAR_BUDGET = 1500

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_FRONTMATTER_RE = re.compile(r"^---\s*$")


def skills_root() -> Path:
    env = os.environ.get("SKILLS_DIR")
    if env:
        return Path(os.path.expanduser(env))
    cwd = Path.cwd() / "skills"
    if cwd.is_dir():
        return cwd
    # Fallback: repo root inferred from this file (mcp-skills/ is a sibling of skills/).
    return Path(__file__).resolve().parent.parent / "skills"


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9_]+", text.lower()) if len(t) > 2]


def _parse_file(path: Path, pack: str) -> list[dict]:
    """Split a reference file into heading-scoped chunks."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    ref_id = f"{pack}/{path.stem}"

    # Strip frontmatter, capture description.
    description = ""
    i = 0
    if lines and _FRONTMATTER_RE.match(lines[0]):
        i = 1
        while i < len(lines) and not _FRONTMATTER_RE.match(lines[i]):
            m = re.match(r"\s*description:\s*['\"]?(.+?)['\"]?\s*$", lines[i])
            if m:
                description = m.group(1)
            i += 1
        i += 1  # skip closing ---

    chunks: list[dict] = []
    cur_heading = description and f"(description) {ref_id}" or ref_id
    cur_lines: list[str] = []
    cur_line_no = i + 1

    def flush(heading: str, body_lines: list[str], line_no: int) -> None:
        body = "\n".join(body_lines).strip()
        if not body and not heading:
            return
        chunks.append(
            {
                "ref_id": ref_id,
                "pack": pack,
                "heading": heading,
                "body": body,
                "path": str(path),
                "line": line_no,
                "description": description,
            }
        )

    for n in range(i, len(lines)):
        line = lines[n]
        hm = _HEADING_RE.match(line)
        if hm:
            flush(cur_heading, cur_lines, cur_line_no)
            cur_heading = hm.group(2).strip()
            cur_lines = []
            cur_line_no = n + 1
        else:
            cur_lines.append(line)
    flush(cur_heading, cur_lines, cur_line_no)
    return chunks


def build_index(root: Path | None = None) -> list[dict]:
    base = root or skills_root()
    index: list[dict] = []
    if not base.is_dir():
        return index
    for ref in sorted(base.glob("*/references/*.md")):
        pack = ref.parent.parent.name
        index.extend(_parse_file(ref, pack))
    return index


def _score(chunk: dict, terms: list[str]) -> int:
    if not terms:
        return 0
    heading_terms = set(_tokenize(chunk["heading"]))
    body_terms = _tokenize(chunk["body"])
    body_set = set(body_terms)
    score = 0
    for t in terms:
        if t in heading_terms:
            score += 5
        if t in body_set:
            score += 1
    # Small boost if ref_id/pack mentions the term.
    id_terms = set(_tokenize(chunk["ref_id"]))
    score += sum(2 for t in terms if t in id_terms)
    return score


def _truncate(body: str, limit: int = PER_CHUNK_CHARS) -> str:
    if len(body) <= limit:
        return body
    return body[: limit - 1].rstrip() + "…"


def search_refs(query: str, pack: str | None = None, k: int = 3, index: list[dict] | None = None) -> dict:
    idx = index if index is not None else build_index()
    terms = _tokenize(query)
    scored = []
    for ch in idx:
        if pack and ch["pack"] != pack:
            continue
        s = _score(ch, terms)
        if s > 0:
            scored.append((s, ch))
    scored.sort(key=lambda x: (-x[0], x[1]["ref_id"], x[1]["line"]))

    results = []
    used = 0
    for s, ch in scored[: max(k * 2, k)]:
        snippet = _truncate(ch["body"])
        entry = {
            "ref_id": ch["ref_id"],
            "pack": ch["pack"],
            "heading": ch["heading"],
            "snippet": snippet,
            "path": ch["path"],
            "line": ch["line"],
            "score": s,
        }
        size = len(snippet) + len(ch["heading"]) + len(ch["ref_id"]) + 40
        if used + size > SEARCH_CHAR_BUDGET and results:
            break
        results.append(entry)
        used += size
        if len(results) >= k:
            break
    return {"query": query, "pack": pack, "results": results}


def get_ref_section(ref_id: str, heading: str | None = None, index: list[dict] | None = None) -> dict:
    idx = index if index is not None else build_index()
    matches = [ch for ch in idx if ch["ref_id"] == ref_id]
    if not matches:
        return {"ref_id": ref_id, "found": False, "sections": []}
    if heading:
        h = heading.strip().lower()
        sel = [ch for ch in matches if ch["heading"].strip().lower() == h]
        if not sel:
            sel = [ch for ch in matches if h in ch["heading"].strip().lower()]
        matches = sel or matches[:1]
    sections = [
        {"heading": ch["heading"], "body": _truncate(ch["body"], PER_CHUNK_CHARS * 2), "line": ch["line"]}
        for ch in matches[:3]
    ]
    return {"ref_id": ref_id, "found": True, "sections": sections}


def list_refs(pack: str | None = None, index: list[dict] | None = None) -> dict:
    idx = index if index is not None else build_index()
    refs: dict[str, dict] = {}
    for ch in idx:
        if pack and ch["pack"] != pack:
            continue
        r = refs.setdefault(ch["ref_id"], {"ref_id": ch["ref_id"], "pack": ch["pack"], "headings": []})
        h = ch["heading"]
        if h and h not in r["headings"] and not h.startswith("(description)"):
            r["headings"].append(h)

    out = []
    used = 0
    for r in sorted(refs.values(), key=lambda x: x["ref_id"]):
        r["headings"] = r["headings"][:8]
        size = len(r["ref_id"]) + sum(len(h) for h in r["headings"]) + 20
        if used + size > LIST_CHAR_BUDGET and out:
            break
        out.append(r)
        used += size
    return {"pack": pack, "count": len(out), "refs": out}


def stats(index: list[dict] | None = None) -> dict:
    idx = index if index is not None else build_index()
    refs = {ch["ref_id"] for ch in idx}
    packs = {ch["pack"] for ch in idx}
    return {"references": len(refs), "packs": len(packs), "chunks": len(idx)}

