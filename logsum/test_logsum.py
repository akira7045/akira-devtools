#!/usr/bin/env python3
"""Tests for logsum. Run: python3 test_logsum.py"""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logsum


def write_tmp(lines):
    fd, path = tempfile.mkstemp(suffix=".log", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


ACCESS = [
    '1.2.3.4 - - [09/Nov/2026:12:00:00 +0000] "GET /a" 200 12',
    '1.2.3.4 - - [09/Nov/2026:12:00:01 +0000] "POST /b" 201 34',
    '5.6.7.8 - - [09/Nov/2026:12:00:02 +0000] "GET /a" 404 0',
    "this line does not match anything",
]


class TestAccess(unittest.TestCase):
    def test_status_counts(self):
        p = write_tmp(ACCESS)
        try:
            r = logsum.summarize([p], fmt="access")
        finally:
            os.unlink(p)
        self.assertEqual(r["total"], 4)
        self.assertEqual(r["matched"], 3)
        d = dict(r["top"])
        self.assertEqual(d["200"], 1)
        self.assertEqual(d["201"], 1)
        self.assertEqual(d["404"], 1)

    def test_by_method(self):
        p = write_tmp(ACCESS)
        try:
            r = logsum.summarize([p], fmt="access", by="method")
        finally:
            os.unlink(p)
        d = dict(r["top"])
        self.assertEqual(d["GET"], 2)
        self.assertEqual(d["POST"], 1)

    def test_by_path(self):
        p = write_tmp(ACCESS)
        try:
            r = logsum.summarize([p], fmt="access", by="path")
        finally:
            os.unlink(p)
        self.assertEqual(dict(r["top"])["/a"], 2)

    def test_auto_detects_access(self):
        p = write_tmp(ACCESS)
        try:
            r = logsum.summarize([p], fmt="auto")
        finally:
            os.unlink(p)
        self.assertEqual(r["matched"], 3)


SYSLOG = [
    "Nov  9 12:00:00 host sshd[123]: Accepted publickey for akira",
    "Nov  9 12:00:01 host cron[456]: job ran",
    "Nov  9 12:00:02 host sshd[789]: Accepted password",
]


class TestSyslog(unittest.TestCase):
    def test_by_app(self):
        p = write_tmp(SYSLOG)
        try:
            r = logsum.summarize([p], fmt="syslog", by="app")
        finally:
            os.unlink(p)
        d = dict(r["top"])
        self.assertEqual(d["sshd"], 2)
        self.assertEqual(d["cron"], 1)


JSONL = [
    '{"level":"info","msg":"ok"}',
    '{"level":"error","msg":"boom"}',
    '{"level":"error","msg":"boom2"}',
    '{"level":"info","msg":"ok2"}',
    "not json at all",
]


class TestJsonl(unittest.TestCase):
    def test_level_counts(self):
        p = write_tmp(JSONL)
        try:
            r = logsum.summarize([p], fmt="jsonl", by="level")
        finally:
            os.unlink(p)
        self.assertEqual(r["matched"], 4)
        d = dict(r["top"])
        self.assertEqual(d["info"], 2)
        self.assertEqual(d["error"], 2)

    def test_auto(self):
        p = write_tmp(JSONL)
        try:
            r = logsum.summarize([p], fmt="auto", by="level")
        finally:
            os.unlink(p)
        self.assertEqual(r["matched"], 4)


class TestGeneric(unittest.TestCase):
    def test_kv_fallback(self):
        p = write_tmp(["level=warn user=akira", "level=warn user=akira", "level=info"])
        try:
            r = logsum.summarize([p], fmt="auto", by="level")
        finally:
            os.unlink(p)
        d = dict(r["top"])
        self.assertEqual(d["warn"], 2)
        self.assertEqual(d["info"], 1)


class TestMain(unittest.TestCase):
    def test_stdin(self):
        old = sys.stdin
        sys.stdin = io.StringIO("\n".join(JSONL) + "\n")
        try:
            rc = logsum.main(["-", "--format", "jsonl", "--json"])
        finally:
            sys.stdin = old
        self.assertEqual(rc, 0)

    def test_json_output_shape(self):
        p = write_tmp(ACCESS)
        try:
            result = logsum.summarize([p], fmt="access", top=2)
        finally:
            os.unlink(p)
        self.assertLessEqual(len(result["top"]), 2)

    def test_no_match_returns_1(self):
        p = write_tmp(["nothing here"])
        try:
            rc = logsum.main([p, "--format", "access"])
        finally:
            os.unlink(p)
        self.assertEqual(rc, 1)

    def test_missing_file_returns_2(self):
        rc = logsum.main(["/no/such/file.log", "--format", "access"])
        self.assertEqual(rc, 2)

    def test_top_default_cap(self):
        lines = [f'{{"level":"l{i:02d}"}}' for i in range(30)]
        p = write_tmp(lines)
        try:
            r = logsum.summarize([p], fmt="jsonl", top=10)
        finally:
            os.unlink(p)
        self.assertEqual(len(r["top"]), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
