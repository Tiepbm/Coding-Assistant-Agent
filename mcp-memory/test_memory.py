#!/usr/bin/env python3
"""Stdlib-only tests for memory_core. Run: python3 test_memory.py"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import memory_core as mc


class MemoryCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = Path(self.tmp) / "test.db"
        self.conn = mc.connect(self.db)

    def tearDown(self):
        self.conn.close()

    def test_record_and_stats(self):
        mc.record_outcome(self.conn, prompt_summary="payment idempotency",
                          packs="backend-pack,database-pack", domain="banking",
                          risk_class="medium", outcome="accepted")
        stats = mc.get_stats(self.conn)
        self.assertEqual(stats["interactions"], 1)
        self.assertEqual(stats["corrections"], 0)
        self.assertEqual(stats["routing_accuracy_proxy"], 1.0)

    def test_pattern_confidence_accepted_high(self):
        for _ in range(3):
            mc.record_outcome(self.conn, prompt_summary="payment idempotency",
                              packs="backend-pack", domain="banking", outcome="accepted")
        rows = self.conn.execute("SELECT confidence FROM patterns").fetchall()
        self.assertEqual(rows[0]["confidence"], 1.0)

    def test_rejected_lowers_confidence(self):
        mc.record_outcome(self.conn, prompt_summary="x", packs="frontend-pack",
                          domain="banking", outcome="accepted")
        mc.record_outcome(self.conn, prompt_summary="x", packs="frontend-pack",
                          domain="banking", outcome="rejected")
        row = self.conn.execute("SELECT confidence FROM patterns").fetchone()
        self.assertEqual(row["confidence"], 0.5)  # (1.0 + 0.0)/2

    def test_recall_finds_pattern(self):
        for _ in range(2):
            mc.record_outcome(self.conn, prompt_summary="payment idempotency retry",
                              packs="backend-pack,database-pack", domain="banking",
                              outcome="accepted")
        res = mc.recall(self.conn, "payment idempotency", k=3)
        self.assertTrue(res["patterns"])
        self.assertIn("backend-pack", res["patterns"][0]["packs"])

    def test_recall_is_bounded(self):
        for i in range(30):
            mc.record_outcome(self.conn, prompt_summary=f"topic {i} payment",
                              packs=f"pack-{i},database-pack", domain="banking",
                              outcome="accepted")
        import json
        res = mc.recall(self.conn, "payment", k=3)
        self.assertLessEqual(len(json.dumps(res)), mc.RECALL_CHAR_BUDGET + 50)
        self.assertLessEqual(len(res["patterns"]), 3)

    def test_search_memory_index_returns_ids(self):
        mc.record_outcome(self.conn, prompt_summary="payment idempotency incident",
                          packs="backend-pack,database-pack", domain="banking",
                          outcome="accepted")
        res = mc.search_memory_index(self.conn, "payment idempotency", k=5)
        self.assertTrue(res["results"])
        self.assertIn("id", res["results"][0])

    def test_get_memory_details_by_ids(self):
        rid = mc.record_outcome(self.conn, prompt_summary="release rollback decision",
                                packs="observability-release-pack", domain="platform",
                                refs="backend-pack/java", outcome="edited")
        details = mc.get_memory_details(self.conn, [rid])
        self.assertEqual(len(details["details"]), 1)
        self.assertEqual(details["details"][0]["id"], rid)
        self.assertIn("observability-release-pack", details["details"][0]["packs"])

    def test_memory_index_and_details_are_bounded(self):
        for i in range(40):
            mc.record_outcome(self.conn, prompt_summary=f"payment topic {i} with long text",
                              packs=f"pack-{i},database-pack", domain="banking",
                              refs="ref-a,ref-b,ref-c", outcome="accepted")
        import json
        idx = mc.search_memory_index(self.conn, "payment", k=25)
        det = mc.get_memory_details(self.conn, [r["id"] for r in idx["results"]])
        self.assertLessEqual(len(json.dumps(idx)), mc.INDEX_CHAR_BUDGET + 80)
        self.assertLessEqual(len(json.dumps(det)), mc.DETAILS_CHAR_BUDGET + 80)

    def test_search_memory_index_caps_k(self):
        for i in range(25):
            mc.record_outcome(self.conn, prompt_summary=f"payment {i}",
                              packs="backend-pack,database-pack", domain="banking",
                              outcome="accepted")
        res = mc.search_memory_index(self.conn, "payment", k=999)
        self.assertLessEqual(len(res["results"]), mc.MAX_INDEX_K)

    def test_get_memory_details_caps_ids(self):
        ids = []
        for i in range(12):
            rid = mc.record_outcome(self.conn, prompt_summary=f"incident {i}",
                                    packs="observability-release-pack", domain="platform",
                                    outcome="accepted")
            ids.append(rid)
        det = mc.get_memory_details(self.conn, ids)
        self.assertLessEqual(len(det["details"]), mc.MAX_DETAIL_IDS)

    def test_correction_penalizes(self):
        mc.record_outcome(self.conn, prompt_summary="migration", packs="core-engineering-pack",
                          domain="banking", outcome="accepted")
        mc.record_correction(self.conn, prompt_summary="migration risk",
                            expected_packs="observability-release-pack",
                            actual_packs="core-engineering-pack",
                            root_cause="treated migration as generic review")
        stats = mc.get_stats(self.conn)
        self.assertEqual(stats["corrections"], 1)
        self.assertLess(stats["routing_accuracy_proxy"], 1.0)

    def test_synthesize_idempotent(self):
        mc.record_outcome(self.conn, prompt_summary="a", packs="backend-pack",
                          domain="banking", outcome="accepted")
        r1 = mc.synthesize(self.conn)
        r2 = mc.synthesize(self.conn)
        self.assertEqual(r1["patterns"], r2["patterns"])

    def test_export(self):
        for _ in range(2):
            mc.record_outcome(self.conn, prompt_summary="payment", packs="backend-pack",
                              domain="banking", outcome="accepted")
        out = Path(self.tmp) / "exported.md"
        n = mc.export_patterns(self.conn, out)
        self.assertGreaterEqual(n, 1)
        self.assertIn("backend-pack", out.read_text())

    def test_report_appends(self):
        mc.record_outcome(self.conn, prompt_summary="payment", packs="backend-pack",
                          domain="banking", outcome="accepted")
        out = Path(self.tmp) / "history.jsonl"
        mc.report_accuracy(self.conn, out)
        mc.report_accuracy(self.conn, out)
        self.assertEqual(len(out.read_text().strip().splitlines()), 2)

    def test_promotion_candidates_patterns(self):
        for _ in range(4):
            mc.record_outcome(self.conn, prompt_summary="payment idempotency",
                              packs="backend-pack,database-pack", domain="banking",
                              outcome="accepted")
        cands = mc.promotion_candidates(self.conn, min_freq=3, min_conf=0.7)
        self.assertTrue(cands["patterns"])
        self.assertEqual(cands["patterns"][0]["frequency"], 4)

    def test_promotion_excludes_low_freq(self):
        mc.record_outcome(self.conn, prompt_summary="rare", packs="frontend-pack",
                          domain="banking", outcome="accepted")
        cands = mc.promotion_candidates(self.conn, min_freq=3, min_conf=0.7)
        self.assertEqual(cands["patterns"], [])

    def test_promotion_corrections_recurrence(self):
        for _ in range(2):
            mc.record_correction(self.conn, prompt_summary="migration risk",
                                expected_packs="observability-release-pack",
                                actual_packs="core-engineering-pack",
                                root_cause="treated migration as generic review")
        cands = mc.promotion_candidates(self.conn, min_corr=2)
        self.assertTrue(cands["corrections"])
        self.assertEqual(cands["corrections"][0]["count"], 2)

    def test_promote_to_file_and_dedup(self):
        for _ in range(4):
            mc.record_outcome(self.conn, prompt_summary="payment idempotency",
                              packs="backend-pack,database-pack", domain="banking",
                              outcome="accepted")
        out = Path(self.tmp) / "learned-patterns.md"
        out.write_text("# Learned Patterns\n", encoding="utf-8")
        r1 = mc.promote_to_file(self.conn, out, min_freq=3, min_conf=0.7)
        self.assertGreaterEqual(r1["appended"], 1)
        self.assertIn("PROPOSED", out.read_text())
        self.assertIn("<!-- promo:", out.read_text())
        # Second run is idempotent — nothing new appended.
        r2 = mc.promote_to_file(self.conn, out, min_freq=3, min_conf=0.7)
        self.assertEqual(r2["appended"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

