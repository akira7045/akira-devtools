#!/usr/bin/env python3
"""Tests for dupfind. Run: python3 test_dupfind.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "dupfind.py")

passed = 0
failed = 0


def run(args, **kw):
    return subprocess.run([sys.executable, TOOL] + args,
                          capture_output=True, text=True, **kw)


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS {name}")
    else:
        failed += 1
        print(f"FAIL {name}")


def make(d, name, data):
    p = os.path.join(d, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return p


def test_no_dups():
    with tempfile.TemporaryDirectory() as d:
        make(d, "a.txt", b"alpha")
        make(d, "b.txt", b"beta")
        r = run([d])
        check("no_dups_exit0", r.returncode == 0)
        check("no_dups_msg", "No duplicates" in r.stdout)


def test_finds_dups():
    with tempfile.TemporaryDirectory() as d:
        make(d, "one/x.bin", b"same-content")
        make(d, "two/y.bin", b"same-content")
        make(d, "z.bin", b"different")
        r = run([d])
        check("dup_exit1", r.returncode == 1)
        check("dup_both_listed", "x.bin" in r.stdout and "y.bin" in r.stdout)
        check("unique_not_listed", "z.bin" not in r.stdout)


def test_json():
    with tempfile.TemporaryDirectory() as d:
        make(d, "a", b"xyz")
        make(d, "b", b"xyz")
        r = run(["--json", d])
        data = json.loads(r.stdout)
        check("json_groups", data["duplicate_groups"] == 1)
        check("json_wasted", data["total_wasted"] == 3)
        check("json_files", len(data["groups"][0]["files"]) == 2)


def test_min_size():
    with tempfile.TemporaryDirectory() as d:
        make(d, "s1", b"ab")
        make(d, "s2", b"ab")
        make(d, "big1", b"X" * 100)
        make(d, "big2", b"X" * 100)
        r = run(["--min-size", "10", d])
        # s1/s2 live in the temp root; their full path legitimately contains
        # the randomized dir name, so match the basename, not a path substring.
        listed = {os.path.basename(l.strip())
                  for l in r.stdout.splitlines() if l.strip().startswith("/")}
        check("minsize_excludes_small", "s1" not in listed)
        check("minsize_keeps_big", "big1" in r.stdout)


def test_empty_flag():
    with tempfile.TemporaryDirectory() as d:
        make(d, "e1", b"")
        make(d, "e2", b"")
        r1 = run([d])
        check("empty_ignored_by_default", r1.returncode == 0)
        r2 = run(["--empty", d])
        check("empty_included", r2.returncode == 1 and "e1" in r2.stdout)


def test_single_file():
    with tempfile.TemporaryDirectory() as d:
        p = make(d, "only.txt", b"data")
        r = run([p])
        check("single_file_ok", r.returncode == 0)


def test_dedupe_script():
    with tempfile.TemporaryDirectory() as d:
        make(d, "keep/a", b"dup")
        make(d, "keep/b", b"dup")
        r = run(["--dedupe-script", d])
        check("script_shebang", r.stdout.startswith("#!/bin/sh"))
        check("script_has_rm", "rm -- " in r.stdout)
        # exactly one rm line for a 2-file group
        rm_lines = [l for l in r.stdout.splitlines() if l.startswith("rm -- ")]
        check("script_one_rm", len(rm_lines) == 1)


def test_missing_path():
    r = run(["/nonexistent/path/xyz"])
    check("missing_exit2", r.returncode == 2)


def test_quotes_handled():
    with tempfile.TemporaryDirectory() as d:
        make(d, "a b/c d.txt", b"q")
        make(d, "a b/e f.txt", b"q")
        r = run(["--dedupe-script", d])
        check("quote_safe", r.stdout.count("rm -- ") == 1)


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
    print(f"\n{passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
