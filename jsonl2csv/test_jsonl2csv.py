#!/usr/bin/env python3
"""Tests for jsonl2csv. Run: python3 test_jsonl2csv.py"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "jsonl2csv.py")


def run(args, stdin=None):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        input=stdin,
        capture_output=True,
        text=True,
    )


def write(tmp, name, content):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_jsonl_basic():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1,"b":2}\n{"a":3,"b":4}\n')
        r = run([p])
        assert r.returncode == 0, r.stderr
        lines = r.stdout.strip().splitlines()
        assert lines[0] == "a,b", lines
        assert lines[1] == "1,2"
        assert lines[2] == "3,4"


def test_json_array():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.json", '[{"x":"u","y":"v"},{"x":"w","y":"z"}]')
        r = run([p])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines() == ["x,y", "u,v", "w,z"]


def test_wrapped_object():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.json", '{"data":[{"k":1},{"k":2}]}')
        r = run([p])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines() == ["k", "1", "2"]


def test_ragged_rows():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1}\n{"a":2,"b":3}\n')
        r = run([p])
        assert r.returncode == 0, r.stderr
        lines = r.stdout.strip().splitlines()
        assert lines[0] == "a,b"
        assert "1," in lines[1] or lines[1] == "1,"
        assert "missing" in r.stderr


def test_flatten_nested():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.json", '[{"user":{"id":7,"name":"ann"},"ok":true}]')
        r = run([p])
        assert r.returncode == 0, r.stderr
        lines = r.stdout.strip().splitlines()
        assert "user.id" in lines[0] and "user.name" in lines[0]
        assert lines[1] == "7,ann,True"


def test_no_flatten():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.json", '[{"u":{"id":7}}]')
        r = run([p, "--no-flatten"])
        assert r.returncode == 0, r.stderr
        assert '"{""id"": 7}"' in r.stdout or '"{""id"":7}"' in r.stdout.replace(" ", "")


def test_columns_order_and_subset():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1,"b":2,"c":3}\n')
        r = run([p, "--columns", "c,a"])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines() == ["c,a", "3,1"]


def test_delimiter():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1,"b":2}\n')
        r = run([p, "--delimiter", ";"])
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip().splitlines()[0] == "a;b"


def test_output_file():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1}\n')
        outp = os.path.join(d, "out.csv")
        r = run([p, "-o", outp])
        assert r.returncode == 0, r.stderr
        with open(outp, encoding="utf-8") as f:
            assert f.read().strip().splitlines() == ["a", "1"]


def test_bad_jsonl_lines_warned():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1}\nnot json\n{"a":2}\n')
        r = run([p])
        assert r.returncode == 0, r.stderr
        assert "invalid JSON" in r.stderr
        assert "wrote 2 rows" in r.stderr


def test_strict_fails_on_ragged():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", '{"a":1}\n{"a":2,"b":3}\n')
        r = run([p, "--strict"])
        assert r.returncode == 1


def test_stdin():
    r = run(["-"], stdin='{"a":1,"b":2}\n{"a":3,"b":4}\n')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines() == ["a,b", "1,2", "3,4"]


def test_empty_input():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "in.jsonl", "")
        r = run([p])
        assert r.returncode == 1


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
