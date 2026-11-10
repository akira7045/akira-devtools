#!/usr/bin/env python3
"""Tests for ga4merge. Run: python3 test_ga4merge.py"""
import csv
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ga4merge


def make_csv(lines):
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


GA4_A = [
    "# Sessions by Session primary channel group",
    'Date range,Session primary channel group,Sessions,Active users',
    '20261009-20261105,Organic Search,120,90',
    '20261009-20261105,Direct,30,25',
]

GA4_B = [
    "# Conversions",
    "Date range,Session primary channel group,Sessions,Active users",
    "20261009-20261105,Organic Search,200,150",
]


class TestRead(unittest.TestCase):
    def test_skips_preamble_and_reads_header(self):
        p = make_csv(GA4_A)
        try:
            header, rows, _ = ga4merge.read_ga4_csv(p)
        finally:
            os.unlink(p)
        self.assertEqual(header[0], "Date range")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][-1], "90")


class TestMerge(unittest.TestCase):
    def test_two_files_same_columns(self):
        p1 = make_csv(GA4_A)
        p2 = make_csv(GA4_B)
        try:
            cols, rows, per = ga4merge.merge([p1, p2])
        finally:
            os.unlink(p1)
            os.unlink(p2)
        self.assertEqual(cols, ["source_file", "Date range", "Session primary channel group", "Sessions", "Active users"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(p["rows"] for p in per), 3)
        self.assertTrue(all("source_file" in r for r in rows))

    def test_union_columns_and_padding(self):
        p1 = make_csv(["# x", "a,b", "1,2"])
        p2 = make_csv(["# y", "a,c", "3,4"])
        try:
            cols, rows, _ = ga4merge.merge([p1, p2])
        finally:
            os.unlink(p1)
            os.unlink(p2)
        self.assertEqual(cols, ["source_file", "a", "b", "c"])
        self.assertEqual(rows[0]["b"], "2")
        self.assertEqual(rows[1]["b"], "")
        self.assertEqual(rows[1]["c"], "4")

    def test_empty_file_marked(self):
        p = make_csv(["# nothing"])
        try:
            cols, rows, per = ga4merge.merge([p])
        finally:
            os.unlink(p)
        self.assertEqual(per[0]["status"], "empty")
        self.assertEqual(rows, [])


class TestCli(unittest.TestCase):
    def _run(self, argv):
        old = sys.stdout
        olderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            code = ga4merge.main(argv)
            return code, sys.stdout.getvalue(), sys.stderr.getvalue()
        finally:
            sys.stdout = old
            sys.stderr = olderr

    def test_unified_diff_style_headers_no_crash(self):
        p1 = make_csv(GA4_A)
        p2 = make_csv(GA4_B)
        out = tempfile.mktemp(suffix=".csv")
        try:
            code, _, _ = self._run([p1, p2, "-o", out])
            self.assertEqual(code, 0)
            with open(out, newline="", encoding="utf-8") as f:
                data = list(csv.DictReader(f))
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0]["source_file"], os.path.basename(p1))
        finally:
            os.unlink(p1)
            os.unlink(p2)
            if os.path.exists(out):
                os.unlink(out)

    def test_missing_file_exit_2(self):
        code, _, err = self._run(["/no/such/file.csv"])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_json_summary(self):
        p = make_csv(GA4_A)
        out = tempfile.mktemp(suffix=".csv")
        try:
            code, stdout, _ = self._run([p, "-o", out, "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(stdout[stdout.index("{"):])
            self.assertEqual(payload["total_rows"], 2)
            self.assertEqual(payload["files"], 1)
        finally:
            os.unlink(p)
            if os.path.exists(out):
                os.unlink(out)

    def test_stdout_mode_writes_rows(self):
        p = make_csv(GA4_A)
        try:
            code, stdout, _ = self._run([p, "--stdout"])
            self.assertEqual(code, 0)
            self.assertIn("source_file", stdout)
            self.assertIn("Organic Search", stdout)
        finally:
            os.unlink(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
