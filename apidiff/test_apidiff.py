#!/usr/bin/env python3
"""Tests for apidiff. Run: python3 test_apidiff.py"""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "apidiff.py")

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


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def start_server(payload):
    """Start a tiny HTTP server that always returns `payload` as JSON."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


def test_identical_files():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"x": 1, "y": [1, 2]})
        write_json(b, {"y": [1, 2], "x": 1})
        r = run(["diff", a, b])
        check("identical_exit0", r.returncode == 0)
        check("identical_msg", "no differences" in r.stdout)


def test_changed_value():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"x": 1})
        write_json(b, {"x": 2})
        r = run(["diff", a, b])
        check("changed_exit1", r.returncode == 1)
        check("changed_kind", "[changed]" in r.stdout)
        check("changed_path", "x" in r.stdout)


def test_added_removed_keys():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"keep": 1, "gone": 2})
        write_json(b, {"keep": 1, "new": 3})
        r = run(["diff", a, b])
        check("added_removed_exit1", r.returncode == 1)
        check("removed_present", "[removed]" in r.stdout)
        check("added_present", "[added" in r.stdout)


def test_type_change():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"v": 1})
        write_json(b, {"v": "1"})
        r = run(["diff", a, b])
        check("type_exit1", r.returncode == 1)
        check("type_kind", "[type" in r.stdout)


def test_nested_diff():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"user": {"name": "a", "tags": ["x"]}})
        write_json(b, {"user": {"name": "b", "tags": ["x"]}})
        r = run(["diff", a, b])
        check("nested_exit1", r.returncode == 1)
        check("nested_path", "user.name" in r.stdout)


def test_list_length():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"items": [1, 2, 3]})
        write_json(b, {"items": [1, 2]})
        r = run(["diff", a, b])
        check("length_exit1", r.returncode == 1)
        check("length_kind", "[length" in r.stdout)


def test_breaking_only_filters_added():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"keep": 1})
        write_json(b, {"keep": 1, "new": 2})
        r_all = run(["diff", a, b])
        check("breaking_added_full_exit1", r_all.returncode == 1)
        r = run(["diff", a, b, "--breaking-only"])
        check("breaking_added_only_exit0", r.returncode == 0)
        check("breaking_added_only_hidden", "[added" not in r.stdout)


def test_breaking_only_keeps_removed_and_type():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"gone": 1, "v": 1})
        write_json(b, {"v": "1"})
        r = run(["diff", a, b, "--breaking-only"])
        check("breaking_removed_type_exit1", r.returncode == 1)
        check("breaking_removed_present", "[removed]" in r.stdout)
        check("breaking_type_present", "[type" in r.stdout)


def test_json_output():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"x": 1})
        write_json(b, {"x": 2})
        r = run(["diff", a, b, "--json"])
        ok = False
        try:
            data = json.loads(r.stdout)
            ok = isinstance(data, list) and data and data[0]["path"] == "x"
        except Exception:
            pass
        check("json_parses", ok)


def test_missing_file_error():
    r = run(["diff", "/no/such/a.json", "/no/such/b.json"])
    check("missing_exit2", r.returncode == 2)


def test_save_and_check_roundtrip():
    srv, url = start_server({"a": 1, "b": {"c": 2}})
    try:
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.json")
            r = run(["save", url, base])
            check("save_exit0", r.returncode == 0)
            check("save_file", os.path.exists(base))
            r2 = run(["check", url, base])
            check("check_identical_exit0", r2.returncode == 0)
    finally:
        srv.shutdown()


def test_check_detects_drift():
    srv1, url1 = start_server({"v": 1})
    srv2, url2 = start_server({"v": 2})
    try:
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "base.json")
            run(["save", url1, base])
            r = run(["check", url2, base])
            check("drift_exit1", r.returncode == 1)
            check("drift_reported", "[changed]" in r.stdout)
    finally:
        srv1.shutdown()
        srv2.shutdown()


def test_bad_header():
    r = run(["save", "http://127.0.0.1:1/", "/tmp/x.json", "--header", "badheader"])
    check("bad_header_exit2", r.returncode == 2)


def start_path_server(payloads):
    """Serve {path: obj}; each request returns the JSON for its path."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            payload = payloads.get(self.path, {"error": "not found"})
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_watch_save_then_check_clean():
    srv, base_url = start_path_server({"/a": {"v": 1}, "/b": {"v": 2}})
    try:
        with tempfile.TemporaryDirectory() as d:
            endpoints = os.path.join(d, "endpoints.json")
            write_json(endpoints, {"a": base_url + "/a", "b": base_url + "/b"})
            out = os.path.join(d, "baselines")
            r = run(["watch", endpoints, out])
            check("watch_save_exit0", r.returncode == 0)
            check("watch_save_a", os.path.exists(os.path.join(out, "a.json")))
            check("watch_save_b", os.path.exists(os.path.join(out, "b.json")))
            r2 = run(["watch", endpoints, out, "--check"])
            check("watch_check_clean_exit0", r2.returncode == 0)
            check("watch_check_ok_msg", "[ok" in r2.stdout)
    finally:
        srv.shutdown()


def test_watch_check_detects_drift():
    srv1, url1 = start_path_server({"/a": {"v": 1}, "/b": {"v": 2}})
    srv2, url2 = start_path_server({"/a": {"v": 1}, "/b": {"v": 999}})
    try:
        with tempfile.TemporaryDirectory() as d:
            ep1 = os.path.join(d, "ep1.json")
            write_json(ep1, {"a": url1 + "/a", "b": url1 + "/b"})
            out = os.path.join(d, "baselines")
            r = run(["watch", ep1, out])
            check("watch_drift_save_exit0", r.returncode == 0)
            ep2 = os.path.join(d, "ep2.json")
            write_json(ep2, {"a": url1 + "/a", "b": url2 + "/b"})
            r2 = run(["watch", ep2, out, "--check"])
            check("watch_drift_exit1", r2.returncode == 1)
            check("watch_drift_msg", "[drift" in r2.stdout)
    finally:
        srv1.shutdown()
        srv2.shutdown()


def test_watch_continues_past_error():
    srv, base_url = start_path_server({"/a": {"v": 1}})
    try:
        with tempfile.TemporaryDirectory() as d:
            endpoints = os.path.join(d, "endpoints.json")
            write_json(endpoints, {"a": base_url + "/a",
                                   "dead": "http://127.0.0.1:1/"})
            out = os.path.join(d, "baselines")
            r = run(["watch", endpoints, out], timeout=20)
            check("watch_error_exit1", r.returncode == 1)
            check("watch_error_continues",
                  os.path.exists(os.path.join(out, "a.json")))
            check("watch_error_reported", "[error" in r.stdout)
    finally:
        srv.shutdown()


def test_watch_bad_endpoints_file():
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "bad.json")
        write_json(bad, [])
        r = run(["watch", bad, os.path.join(d, "out")])
        check("watch_bad_endpoints_exit2", r.returncode == 2)


def test_keyed_array_insert_no_shift_noise():
    """Inserting an item mid-list must not flag every downstream index."""
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"items": [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]})
        write_json(b, {"items": [{"id": 0, "v": "z"}, {"id": 1, "v": "a"},
                                 {"id": 2, "v": "b"}]})
        r = run(["diff", a, b, "--json"])
        data = json.loads(r.stdout)
        kinds = {x["kind"] for x in data}
        check("keyed_insert_exit1", r.returncode == 1)
        check("keyed_insert_only_added", kinds == {"added"})
        check("keyed_insert_path", any("0" in x["path"] for x in data))


def test_keyed_array_removed_item():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"items": [{"id": 1}, {"id": 2}, {"id": 3}]})
        write_json(b, {"items": [{"id": 1}, {"id": 3}]})
        r = run(["diff", a, b, "--json"])
        data = json.loads(r.stdout)
        kinds = {x["kind"] for x in data}
        check("keyed_removed_kind", kinds == {"removed"})


def test_keyed_array_value_change_by_id():
    """Same id, changed value: reported at that id's path, not shifted index."""
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"items": [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]})
        write_json(b, {"items": [{"id": 1, "v": "a"}, {"id": 2, "v": "B"}]})
        r = run(["diff", a, b, "--json"])
        data = json.loads(r.stdout)
        check("keyed_value_kind", len(data) == 1 and data[0]["kind"] == "changed")
        check("keyed_value_path", data and "2" in data[0]["path"])


def test_no_key_falls_back_to_positional():
    """Scalar lists have no id key; positional + length reporting still works."""
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.json")
        b = os.path.join(d, "b.json")
        write_json(a, {"xs": [1, 2, 3]})
        write_json(b, {"xs": [1, 9, 3, 4]})
        r = run(["diff", a, b, "--json"])
        data = json.loads(r.stdout)
        kinds = {x["kind"] for x in data}
        check("fallback_length", "length" in kinds)
        check("fallback_changed", "changed" in kinds)


import unittest


class TestAllCases(unittest.TestCase):
    """Runs the module-level test_* functions so pytest / unittest discover them."""

    def test_all_cases(self):
        before = failed
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                with self.subTest(case=name):
                    fn()
        self.assertEqual(failed, before, f"{failed - before} check(s) failed")


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
    print(f"\n{passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
