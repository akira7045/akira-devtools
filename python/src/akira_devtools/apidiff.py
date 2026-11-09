#!/usr/bin/env python3
"""
apidiff.py - Zero-dependency API response differ / contract checker.

Fetch one or more HTTP endpoints, normalize JSON (or text), and diff against a
stored baseline. Great for detecting breaking changes in APIs you depend on,
or for spot-checking that an endpoint still returns the shape you expect.

Usage:
    python3 apidiff.py save URL BASELINE.json     # capture a baseline
    python3 apidiff.py check URL BASELINE.json    # diff live response vs baseline
    python3 apidiff.py diff A.json B.json         # diff two local JSON files
    python3 apidiff.py watch ENDPOINTS.json DIR   # check many endpoints at once

ENDPOINTS.json maps a name to a URL, e.g. {"status": "https://x/status", ...}.
`watch` saves/checks <DIR>/<name>.json for each, continues past failures, and
exits 1 if any endpoint drifted.

Options:
    --method GET|POST     HTTP method (default GET)
    --header "K: V"       extra header, repeatable
    --data '{"a":1}'      request body (implies POST if --method omitted)
    --ignore KEY[,KEY]    ignore these top-level keys when diffing
    --timeout SECONDS     request timeout (default 15)
    --json                emit the diff as JSON
    --breaking-only       report only contract-breaking changes
                          (removed keys, type changes, array length changes)

Exit code: 0 = no differences, 1 = differences, 2 = error.

License: MIT
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Kinds that indicate a contract-breaking change (existing consumers may fail).
# "added" is non-breaking: new fields/types are generally safe to ignore.
BREAKING_KINDS = {"removed", "type", "length", "changed"}


def only_breaking(diffs):
    return [d for d in diffs if d[3] in BREAKING_KINDS]


def fetch(url, method, headers, data, timeout):
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    body = None
    if data is not None:
        body = data.encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=body, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            ctype = r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        ctype = e.headers.get("Content-Type", "") if e.headers else ""
    except Exception as e:
        raise RuntimeError(f"request failed: {e}")
    return parse_body(raw, ctype)


def parse_body(raw, ctype):
    text = raw.strip()
    if "json" in ctype or text[:1] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return raw


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff(a, b, path="", out=None):
    """Recursively collect differences between a (baseline) and b (live)."""
    if out is None:
        out = []
    if type(a) is not type(b):
        out.append((path or "$", a, b, "type"))
        return out
    if isinstance(a, dict):
        ak, bk = set(a), set(b)
        for k in sorted(ak - bk):
            out.append((join(path, k), a[k], "<missing>", "removed"))
        for k in sorted(bk - ak):
            out.append((join(path, k), "<missing>", b[k], "added"))
        for k in sorted(ak & bk):
            diff(a[k], b[k], join(path, k), out)
        return out
    if isinstance(a, list):
        key = array_key(a, b)
        if key is not None:
            diff_keyed_list(a, b, key, path, out)
            return out
        if len(a) != len(b):
            out.append((f"{path}[len]" if path else "$[len]", len(a), len(b), "length"))
        for i in range(min(len(a), len(b))):
            diff(a[i], b[i], f"{path}[{i}]", out)
        return out
    if a != b:
        out.append((path or "$", a, b, "changed"))
    return out


def join(path, key):
    return f"{path}.{key}" if path else key


def array_key(a, b):
    """Return a shared key field if both lists are dicts that can be aligned
    by a unique identifier, else None (fall back to positional diff).

    Alignment by id avoids the shift noise where inserting one item makes
    every following index look 'changed'. A candidate key must be present in
    every dict of both lists and be unique within each list.
    """
    if not a or not b or not all(isinstance(x, dict) for x in a + b):
        return None
    common = set(a[0]) & set(b[0])
    for k in sorted(common):
        try:
            av = [x[k] for x in a]
            bv = [x[k] for x in b]
        except KeyError:
            continue
        if any(isinstance(v, (dict, list)) for v in av + bv):
            continue
        if len(set(map(repr, av))) == len(av) and len(set(map(repr, bv))) == len(bv):
            return k
    return None


def diff_keyed_list(a, b, key, path, out):
    """Diff two lists of objects aligned by `key`, not by position."""
    amap = {repr(x[key]): x for x in a}
    bmap = {repr(x[key]): x for x in b}
    for k in [x[key] for x in a if repr(x[key]) not in bmap]:
        out.append((f"{path}[{k!r}]" if path else f"$[{k!r}]",
                    amap[repr(k)], "<missing>", "removed"))
    for k in [x[key] for x in b if repr(x[key]) not in amap]:
        out.append((f"{path}[{k!r}]" if path else f"$[{k!r}]",
                    "<missing>", bmap[repr(k)], "added"))
    for x in a:
        if repr(x[key]) in bmap:
            diff(x, bmap[repr(x[key])], f"{path}[{x[key]!r}]" if path else f"$[{x[key]!r}]", out)
    return out


def ignore_keys(obj, keys):
    if not keys or not isinstance(obj, dict):
        return obj
    return {k: v for k, v in obj.items() if k not in keys}


def fmt(v):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 80 else s[:77] + "..."


def parse_headers(header_args):
    headers = {}
    for h in header_args:
        if ":" not in h:
            raise ValueError(f"bad header: {h}")
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


def watch(args):
    """Save or check many endpoints listed in a JSON name->url map."""
    try:
        endpoints = load_json_file(args.endpoints)
    except Exception as e:
        print(f"error: cannot read endpoints file: {e}", file=sys.stderr)
        return 2
    if not isinstance(endpoints, dict) or not endpoints:
        print("error: endpoints file must be a non-empty JSON object", file=sys.stderr)
        return 2
    try:
        headers = parse_headers(args.header)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    method = args.method or ("POST" if args.data else "GET")

    try:
        os.makedirs(args.dir, exist_ok=True)
    except Exception as e:
        print(f"error: cannot create {args.dir}: {e}", file=sys.stderr)
        return 2

    mode = "check" if args.check else "save"
    drifted = False
    results = []
    for name, url in sorted(endpoints.items()):
        baseline = os.path.join(args.dir, f"{name}.json")
        try:
            live = fetch(url, method, headers, args.data, args.timeout)
        except Exception as e:
            results.append({"name": name, "error": str(e)})
            drifted = True
            continue
        if mode == "save":
            with open(baseline, "w", encoding="utf-8") as f:
                json.dump(live, f, indent=2, ensure_ascii=False, sort_keys=True)
            results.append({"name": name, "saved": baseline})
        else:
            try:
                base = load_json_file(baseline)
            except Exception as e:
                results.append({"name": name, "error": f"no baseline: {e}"})
                drifted = True
                continue
            diffs = diff(base, live)
            if getattr(args, "breaking_only", False):
                diffs = only_breaking(diffs)
            if diffs:
                drifted = True
            results.append({"name": name, "diffs": [
                {"path": p_, "baseline": a, "live": b, "kind": k}
                for p_, a, b, k in diffs
            ]})

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if "error" in r:
                print(f"[error  ] {r['name']}: {r['error']}")
            elif "saved" in r:
                print(f"[saved  ] {r['name']} -> {r['saved']}")
            elif not r["diffs"]:
                print(f"[ok     ] {r['name']}")
            else:
                print(f"[drift  ] {r['name']} ({len(r['diffs'])} change(s))")
                for d in r["diffs"]:
                    print(f"    [{d['kind']:7}] {d['path']}")
                    print(f"        - {fmt(d['baseline'])}")
                    print(f"        + {fmt(d['live'])}")
    return 1 if drifted else 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Zero-dependency API response differ.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_http_args(sp):
        sp.add_argument("url")
        sp.add_argument("baseline")
        sp.add_argument("--method", default=None)
        sp.add_argument("--header", action="append", default=[])
        sp.add_argument("--data", default=None)
        sp.add_argument("--timeout", type=float, default=15)
        sp.add_argument("--json", action="store_true")
        sp.add_argument("--breaking-only", action="store_true",
                        help="report only contract-breaking changes")

    ps = sub.add_parser("save", help="capture live response to baseline file")
    add_http_args(ps)
    pc = sub.add_parser("check", help="diff live response against baseline")
    add_http_args(pc)
    pd = sub.add_parser("diff", help="diff two local JSON files")
    pd.add_argument("a")
    pd.add_argument("b")
    pd.add_argument("--json", action="store_true")
    pd.add_argument("--breaking-only", action="store_true",
                    help="report only contract-breaking changes")
    pw = sub.add_parser("watch", help="save or check many endpoints in one run")
    pw.add_argument("endpoints")
    pw.add_argument("dir")
    pw.add_argument("--method", default=None)
    pw.add_argument("--header", action="append", default=[])
    pw.add_argument("--data", default=None)
    pw.add_argument("--timeout", type=float, default=15)
    pw.add_argument("--save", action="store_true",
                    help="write baselines instead of checking (default)")
    pw.add_argument("--check", action="store_true",
                    help="diff live responses against saved baselines")
    pw.add_argument("--json", action="store_true")
    pw.add_argument("--breaking-only", action="store_true",
                    help="report only contract-breaking changes")

    args = p.parse_args(argv)

    try:
        if args.cmd == "watch":
            return watch(args)
        if args.cmd in ("save", "check"):
            try:
                headers = parse_headers(args.header)
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 2
            method = args.method or ("POST" if args.data else "GET")
            live = fetch(args.url, method, headers, args.data, args.timeout)
            if args.cmd == "save":
                with open(args.baseline, "w", encoding="utf-8") as f:
                    json.dump(live, f, indent=2, ensure_ascii=False, sort_keys=True)
                print(f"saved baseline -> {args.baseline}")
                return 0
            base = load_json_file(args.baseline)
            diffs = diff(base, live)
        else:
            diffs = diff(load_json_file(args.a), load_json_file(args.b))
        if getattr(args, "breaking_only", False):
            diffs = only_breaking(diffs)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(
            [{"path": p_, "baseline": a, "live": b, "kind": k} for p_, a, b, k in diffs],
            indent=2, ensure_ascii=False,
        ))
    else:
        if not diffs:
            print("no differences")
        for path, a, b, kind in diffs:
            print(f"[{kind:7}] {path}")
            print(f"    - {fmt(a)}")
            print(f"    + {fmt(b)}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
