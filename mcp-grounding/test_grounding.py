#!/usr/bin/env python3
"""Stdlib-only tests for grounding_core. Run: python3 test_grounding.py"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import grounding_core as gc

GOOD_OPENAPI = """openapi: 3.0.3
info:
  title: Payments
paths:
  /payments/{id}:
    get:
      operationId: getPayment
      responses:
        '200':
          description: ok
"""

BAD_OPENAPI = """info:
  title: Payments
paths: {}
"""

GOOD_PROTO = """syntax = "proto3";
service PaymentService {
  rpc Capture (CaptureRequest) returns (CaptureResponse);
}
message CaptureRequest { string id = 1; }
message CaptureResponse { bool ok = 1; }
"""

BAD_PROTO = """message Broken {
  string id = 1;
"""

GOOD_GRAPHQL = """type Query {
  payment(id: ID!): Payment
}
type Payment { id: ID! amount: Int! }
"""

GOOD_JSON_SCHEMA = '{"$schema":"http://json-schema.org/draft-07/schema#","type":"object","properties":{"id":{"type":"string"}}}'


class GroundingTest(unittest.TestCase):
    def test_detect_and_check_openapi_good(self):
        res = gc.check_contract(GOOD_OPENAPI)
        self.assertEqual(res["format"], "openapi")
        self.assertTrue(res["ok"], res)

    def test_openapi_bad_missing_version_and_paths(self):
        res = gc.check_contract(BAD_OPENAPI, "openapi")
        self.assertFalse(res["ok"])
        self.assertTrue(any("version" in e for e in res["errors"]))

    def test_proto_good(self):
        res = gc.check_contract(GOOD_PROTO)
        self.assertEqual(res["format"], "proto")
        self.assertTrue(res["ok"], res)

    def test_proto_unbalanced_braces(self):
        res = gc.check_contract(BAD_PROTO, "proto")
        self.assertFalse(res["ok"])
        self.assertTrue(any("brace" in e for e in res["errors"]))

    def test_graphql_good(self):
        res = gc.check_contract(GOOD_GRAPHQL)
        self.assertEqual(res["format"], "graphql")
        self.assertTrue(res["ok"], res)

    def test_json_schema(self):
        res = gc.check_contract(GOOD_JSON_SCHEMA)
        self.assertEqual(res["format"], "json")
        self.assertTrue(res["ok"], res)

    def test_empty_contract(self):
        res = gc.check_contract("   ")
        self.assertFalse(res["ok"])

    def test_run_validator_missing(self):
        tmp = Path(tempfile.mkdtemp())
        res = gc.run_validator(str(tmp))
        self.assertFalse(res["ok"])
        self.assertFalse(res["found"])

    def test_handoff_identical(self):
        tmp = Path(tempfile.mkdtemp())
        a = tmp / "HANDOFF-PROTOCOL.md"
        b = tmp / "other.md"
        a.write_text("same\n", encoding="utf-8")
        b.write_text("same\n", encoding="utf-8")
        res = gc.handoff_diff(str(a), str(b))
        self.assertTrue(res["ok"])
        self.assertTrue(res["identical"])

    def test_handoff_diff_detected(self):
        tmp = Path(tempfile.mkdtemp())
        a = tmp / "HANDOFF-PROTOCOL.md"
        b = tmp / "other.md"
        a.write_text("local line\n", encoding="utf-8")
        b.write_text("other line\n", encoding="utf-8")
        res = gc.handoff_diff(str(a), str(b))
        self.assertFalse(res["ok"])
        self.assertFalse(res["identical"])
        self.assertIn("diff", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)

