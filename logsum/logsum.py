#!/usr/bin/env python3
"""logsum - summarize common log formats into counts. Zero dependencies.

Reads one or more log files (or stdin with -) and reports a compact summary:
total lines, matched lines, and top entries grouped by a chosen key (status
code, level, or an explicit field). Safe: read-only, never modifies anything.

Supported inputs (auto or forced with --format):
  auto    - sniff per line; falls back to generic key=value / text rules
  access  - Common/Combined Log Format:  IP - - [time] "GET /p" 200 123
  syslog  - RFC3164-ish:                 Nov  9 12:00:00 host app[pid]: msg
  jsonl   - one JSON object per line (fields: level, status, msg, ...)

Usage:
  logsum.py access.log
  logsum.py --format access --by status access.log
  logsum.py --by level app.jsonl
  cat app.log | logsum.py - --by level
  logsum.py --top 20 --json app.log

Exit codes: 0 = ok, 1 = no lines matched, 2 = usage/IO error.
"""
import argparse
import json
import re
import sys

_ACCESS = re.compile(r'^\S+ \S+ \S+ \[[^\]]+\] "([^"]*)" (\d{3}) (\S+)')
_SYSLOG = re.compile(r"^[A-Z][a-z]{2}\s+\d{1,2} \d{2}:\d{2}:\d{2} \S+ ([^:\[]+)[:\[]?")
_KV = re.compile(r"(\w+)=(\"[^\"]*\"|\S+)")


def parse_access(line):
    m = _ACCESS.match(line)
    if not m:
        return None
    req, status, size = m.group(1), m.group(2), m.group(3)
    parts = req.split()
    method = parts[0] if parts else "-"
    path = parts[1] if len(parts) > 1 else "-"
    return {"status": status, "method": method, "path": path, "level": status}


def parse_syslog(line):
    m = _SYSLOG.match(line)
    if not m:
        return None
    return {"app": m.group(1), "level": m.group(1), "status": "-"}


def parse_jsonl(line):
    s = line.strip()
    if not s.startswith("{"):
        return None
    try:
        obj = json.loads(s)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    out = {k: str(v) for k, v in obj.items() if not isinstance(v, (dict, list))}
    out.setdefault("level", out.get("status", "-"))
    return out


def parse_auto(line):
    for fn in (parse_access, parse_jsonl, parse_syslog):
        r = fn(line)
        if r:
            return r
    kv = dict(_KV.findall(line))
    if kv:
        kv = {k: v.strip('"') for k, v in kv.items()}
        kv.setdefault("level", kv.get("status", "-"))
        return kv
    return None


PARSERS = {
    "auto": parse_auto,
    "access": parse_access,
    "syslog": parse_syslog,
    "jsonl": parse_jsonl,
}


def read_lines(paths):
    for p in paths:
        if p == "-":
            for line in sys.stdin:
                yield line.rstrip("\n")
        else:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    yield line.rstrip("\n")


def summarize(paths, fmt="auto", by="status", top=10):
    parse = PARSERS[fmt]
    total = matched = 0
    counts = {}
    for line in read_lines(paths):
        if not line.strip():
            continue
        total += 1
        rec = parse(line)
        if rec is None:
            continue
        matched += 1
        key = rec.get(by, rec.get("level", "-"))
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))[:top]
    return {"total": total, "matched": matched, "by": by, "top": ranked}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Summarize logs into counts (zero deps).")
    ap.add_argument("paths", nargs="+", help="log file(s), or - for stdin")
    ap.add_argument("--format", choices=sorted(PARSERS), default="auto")
    ap.add_argument("--by", default="status", help="field to group by (default: status)")
    ap.add_argument("--top", type=int, default=10, help="show top N keys (default 10)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args(argv)
    try:
        result = summarize(args.paths, args.format, args.by, args.top)
    except OSError as e:
        print(f"logsum: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"total lines : {result['total']}")
        print(f"matched     : {result['matched']}")
        print(f"grouped by  : {result['by']}")
        if result["top"]:
            width = max(len(str(k)) for k, _ in result["top"])
            for k, n in result["top"]:
                print(f"  {str(k):<{width}}  {n}")
    return 0 if result["matched"] else 1


if __name__ == "__main__":
    sys.exit(main())
