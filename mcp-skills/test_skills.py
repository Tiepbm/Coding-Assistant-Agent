#!/usr/bin/env python3
"""Stdlib-only tests for skills_core. Run: python3 test_skills.py"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import skills_core as sc


def _make_ref(root: Path, pack: str, name: str, body: str) -> None:
    d = root / pack / "references"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(body, encoding="utf-8")


SAMPLE = """---
name: 'java-spring-boot'
description: 'Use when implementing Spring Boot services'
---
# Java Spring Boot

Intro line.

## Idempotency

Use an idempotency key (tenant_id, request_id). Store in a dedup table.
Return the same response on retry.

## Pagination

Use keyset pagination, not OFFSET, for large tables.

### N+1 Queries

Avoid N+1 by using fetch joins or entity graphs.
"""


class SkillsCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _make_ref(self.tmp, "backend-pack", "java-spring-boot", SAMPLE)
        _make_ref(self.tmp, "database-pack", "sql-patterns",
                  "---\ndescription: 'Use when writing SQL'\n---\n# SQL\n\n## Indexes\n\nUse covering indexes.\n")
        self.index = sc.build_index(self.tmp)

    def test_build_index_chunks(self):
        self.assertTrue(self.index)
        ids = {c["ref_id"] for c in self.index}
        self.assertIn("backend-pack/java-spring-boot", ids)
        headings = {c["heading"] for c in self.index if c["ref_id"].endswith("java-spring-boot")}
        self.assertIn("Idempotency", headings)
        self.assertIn("Pagination", headings)
        self.assertIn("N+1 Queries", headings)

    def test_search_returns_matching_section(self):
        res = sc.search_refs("idempotency key retry", k=3, index=self.index)
        self.assertTrue(res["results"])
        top = res["results"][0]
        self.assertEqual(top["heading"], "Idempotency")
        self.assertIn("dedup table", top["snippet"])

    def test_search_pack_filter(self):
        res = sc.search_refs("index", pack="database-pack", k=3, index=self.index)
        self.assertTrue(all(r["pack"] == "database-pack" for r in res["results"]))

    def test_search_bounded(self):
        import json
        res = sc.search_refs("idempotency pagination index sql", k=3, index=self.index)
        self.assertLessEqual(len(json.dumps(res)), sc.SEARCH_CHAR_BUDGET + 400)
        self.assertLessEqual(len(res["results"]), 3)

    def test_get_section_exact(self):
        sec = sc.get_ref_section("backend-pack/java-spring-boot", "Idempotency", index=self.index)
        self.assertTrue(sec["found"])
        self.assertEqual(sec["sections"][0]["heading"], "Idempotency")

    def test_get_section_partial_heading(self):
        sec = sc.get_ref_section("backend-pack/java-spring-boot", "pagin", index=self.index)
        self.assertTrue(sec["found"])
        self.assertEqual(sec["sections"][0]["heading"], "Pagination")

    def test_list_refs(self):
        out = sc.list_refs("backend-pack", index=self.index)
        self.assertEqual(out["count"], 1)
        self.assertIn("Idempotency", out["refs"][0]["headings"])

    def test_retrieval_smaller_than_fullfile(self):
        # The matched snippet must be smaller than the whole file body.
        full = sum(len(c["body"]) for c in self.index if c["ref_id"].endswith("java-spring-boot"))
        res = sc.search_refs("idempotency", k=1, index=self.index)
        snippet = res["results"][0]["snippet"]
        self.assertLess(len(snippet), full)

    def test_no_match_empty(self):
        res = sc.search_refs("zzzznonexistentxyz", k=3, index=self.index)
        self.assertEqual(res["results"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

