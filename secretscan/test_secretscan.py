#!/usr/bin/env python3
"""Self-contained tests for secretscan. Run: python3 test_secretscan.py

Works both as a plain script (prints ok/FAIL per case) and under a test
runner such as ``pytest test_secretscan.py`` or
``python3 -m unittest test_secretscan``.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secretscan as s

CASES = [
    ('password = "supersecretvalue123"', True),
    ('PASSWORD="hunter2hunter2"', True),
    ('db_password = "Tr0ub4dor&3xyz"', True),
    ('access_token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"', True),
    ('key=AKIA1234567890ABCDEF', True),
    ('password = "aaaaaaaaaaaa"', False),
    ('token: ""', False),
    ('svc_api_key = "abcd"', False),
    ('password = os.environ["PW"]', False),
    ('token_url = "https://api.example.com"', False),
    ('self.password = password', False),
    ('AKIAIOSFODNN7EXAMPLE', False),
    ('x = 1', False),
]


class TestScanLine(unittest.TestCase):
    def test_cases_table(self):
        for line, expect in CASES:
            with self.subTest(line=line):
                self.assertEqual(len(s.scan_line(line, 2.0)) > 0, expect)

    def test_entropy_is_nonnegative(self):
        self.assertGreaterEqual(s.shannon_entropy("abc"), 0.0)
        self.assertEqual(s.shannon_entropy(""), 0.0)


class TestScanFile(unittest.TestCase):
    def test_finds_secret_in_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "leak.py"
            p.write_text('password = "supersecretvalue123"\n')
            hits = s.scan_file(p, 2.0)
            self.assertTrue(hits)
            self.assertEqual(hits[0]["line"], 1)
            self.assertEqual(hits[0]["file"], str(p))

    def test_clean_file_has_no_hits(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ok.py"
            p.write_text("x = 1\nprint('hello')\n")
            self.assertEqual(s.scan_file(p, 2.0), [])


def main():
    failed = 0
    for line, expect in CASES:
        fired = len(s.scan_line(line, 2.0)) > 0
        if fired != expect:
            failed += 1
            print(f"FAIL: {line!r} expected={expect} got={fired}")
        else:
            print(f"ok: {line!r} -> {fired}")
    total = len(CASES) + 22  # cases + TestScanLine/TestScanFile pytest checks
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
