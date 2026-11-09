#!/usr/bin/env python3
"""Tests for registry.py — run: python3 test_registry.py (no deps)."""
import csv
import json
import os
import tempfile
import unittest

import registry as R


def _write_csv(rows, header=("sku", "title", "price", "stock")):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


class TestLoad(unittest.TestCase):
    def test_load_ok(self):
        path = _write_csv([["A1", "Item A", "1000", "5"]])
        ps = R.load_products(path)
        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0].sku, "A1")
        self.assertEqual(ps[0].price, 1000)
        os.unlink(path)

    def test_missing_column(self):
        path = _write_csv([["A1", "x"]], header=("sku", "title"))
        with self.assertRaises(ValueError):
            R.load_products(path)
        os.unlink(path)

    def test_empty_sku(self):
        path = _write_csv([["", "Item", "1", "1"]])
        with self.assertRaises(ValueError):
            R.load_products(path)
        os.unlink(path)

    def test_bad_price(self):
        path = _write_csv([["A1", "Item", "abc", "1"]])
        with self.assertRaises(ValueError):
            R.load_products(path)
        os.unlink(path)

    def test_negative_stock(self):
        path = _write_csv([["A1", "Item", "1", "-3"]])
        with self.assertRaises(ValueError):
            R.load_products(path)
        os.unlink(path)


class TestIdempotency(unittest.TestCase):
    def test_key_stable(self):
        p = R.Product("A1", "Item", 100, 5)
        self.assertEqual(R.idempotency_key(p), R.idempotency_key(p))

    def test_key_changes_with_content(self):
        a = R.Product("A1", "Item", 100, 5)
        b = R.Product("A1", "Item", 101, 5)
        self.assertNotEqual(R.idempotency_key(a), R.idempotency_key(b))

    def test_duplicate_not_resent(self):
        calls = []

        def transport(p):
            calls.append(p.sku)

        w = R.Worker(transport=transport, max_attempts=1)
        p = R.Product("A1", "Item", 100, 5)
        r1 = w.register_one(p)
        r2 = w.register_one(p)
        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        self.assertEqual(r2.attempts, 0)  # skipped via idempotency key
        self.assertEqual(calls, ["A1"])


class TestRetry(unittest.TestCase):
    def test_retry_then_success(self):
        state = {"n": 0}

        def flaky(p):
            state["n"] += 1
            if state["n"] < 3:
                raise RuntimeError("transient")

        w = R.Worker(transport=flaky, max_attempts=3, base_delay=0)
        r = w.register_one(R.Product("A1", "Item", 100, 5))
        self.assertTrue(r.ok)
        self.assertEqual(r.attempts, 3)

    def test_exhausted_attempts(self):
        def always_fail(p):
            raise RuntimeError("down")

        w = R.Worker(transport=always_fail, max_attempts=2, base_delay=0)
        r = w.register_one(R.Product("A1", "Item", 100, 5))
        self.assertFalse(r.ok)
        self.assertEqual(r.attempts, 2)
        self.assertIn("down", r.error)


class TestReport(unittest.TestCase):
    def test_report_counts(self):
        products = [R.Product(f"K{i}", "t", 1, 1) for i in range(3)]
        fail_sku = "K1"

        def transport(p):
            if p.sku == fail_sku:
                raise RuntimeError("boom")

        w = R.Worker(transport=transport, max_attempts=1)
        results = w.register_all(products)
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        R.write_report(results, path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["ok"], 2)
        self.assertEqual(data["failed"], 1)
        failed_skus = [i["sku"] for i in data["items"] if not i["ok"]]
        self.assertEqual(failed_skus, [fail_sku])
        os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
