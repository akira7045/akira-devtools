#!/usr/bin/env python3
"""
jsonl2csv.py - Zero-dependency JSON/JSONL to CSV converter & validator.

Turn newline-delimited JSON (JSONL) or a JSON array of objects into a clean CSV.
Handles ragged records (missing keys), nested values (flattened), and type
coercion, while reporting data-quality issues to stderr.

Usage:
    python3 jsonl2csv.py input.jsonl                 # CSV to stdout
    python3 jsonl2csv.py input.json > out.csv
    python3 jsonl2csv.py input.jsonl -o out.csv      # write to file
    python3 jsonl2csv.py input.json --delimiter ';'
    python3 jsonl2csv.py input.json --no-flatten     # keep nested as JSON string
    python3 jsonl2csv.py input.json --columns a,b,c  # force column order
    python3 jsonl2csv.py input.json --strict         # fail on ragged/bad rows

Options:
    -o, --output PATH      write CSV to PATH instead of stdout
    --delimiter CHAR       CSV delimiter (default ',')
    --no-flatten           do not flatten nested objects/arrays (emit JSON text)
    --columns LIST         comma-separated column order (subset or reorder)
    --strict               exit 1 if any row has missing keys or parse error
    --quiet                suppress stderr warnings

Supports .json (array of objects, or {"data": [...]}) and .jsonl (one object per line).

Exit code: 0 = ok, 1 = data problems in --strict mode / no input, 2 = usage error.

License: MIT
"""
import argparse
import csv
import json
import sys


def log(msg, quiet):
    if not quiet:
        print(msg, file=sys.stderr)


def flatten(obj, parent="", out=None):
    """Flatten nested dicts into dotted keys. Arrays become JSON strings."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{parent}.{k}" if parent else str(k)
            if isinstance(v, dict):
                flatten(v, key, out)
            elif isinstance(v, list):
                out[key] = json.dumps(v, ensure_ascii=False)
            else:
                out[key] = v
    else:
        out[parent] = obj
    return out


def load_records(path):
    """Load a JSON array or JSONL stream. Returns (records, errors)."""
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise SystemExit(f"error: cannot read {path}: {e}")

    stripped = text.strip()
    if not stripped:
        return [], ["empty input"]

    # Try whole-file JSON first (array or wrapped object).
    try:
        doc = json.loads(stripped)
        if isinstance(doc, list):
            rows = [r for r in doc if isinstance(r, dict)]
            if len(rows) != len(doc):
                errors.append(f"{len(doc) - len(rows)} non-object entries skipped")
            return rows, errors
        if isinstance(doc, dict):
            # common wrapper: {"data": [...]} / {"items": [...]} / {"results": [...]}
            for k in ("data", "items", "results", "rows", "records"):
                if isinstance(doc.get(k), list):
                    return [r for r in doc[k] if isinstance(r, dict)], errors
            return [doc], errors
        errors.append("top-level JSON is not an object or array")
        return [], errors
    except json.JSONDecodeError:
        pass

    # Fall back to JSONL.
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON ({e.msg})")
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            errors.append(f"line {i}: not a JSON object")
    return rows, errors


def main(argv=None):
    p = argparse.ArgumentParser(description="Convert JSON/JSONL to CSV (zero dependency).")
    p.add_argument("input", help="input .json or .jsonl file ('-' for stdin)")
    p.add_argument("-o", "--output", help="write CSV to this path")
    p.add_argument("--delimiter", default=",", help="CSV delimiter (default ',')")
    p.add_argument("--no-flatten", action="store_true", help="keep nested values as JSON text")
    p.add_argument("--columns", help="comma-separated column order")
    p.add_argument("--strict", action="store_true", help="exit 1 on ragged rows / errors")
    p.add_argument("--quiet", action="store_true", help="suppress warnings")
    args = p.parse_args(argv)

    if len(args.delimiter) != 1:
        print("error: --delimiter must be a single character", file=sys.stderr)
        return 2

    if args.input == "-":
        text = sys.stdin.read()
        tmp_rows, tmp_errors = load_records_from_text(text)
        records, errors = tmp_rows, tmp_errors
    else:
        records, errors = load_records(args.input)

    for e in errors:
        log(f"warning: {e}", args.quiet)

    if not records:
        log("error: no valid records found", args.quiet)
        return 1

    # Flatten and collect all keys (stable order of first appearance).
    flat_rows = []
    keys = []
    seen = set()
    ragged = 0
    for r in records:
        fr = r if args.no_flatten else flatten(r)
        flat_rows.append(fr)
        for k in fr:
            if k not in seen:
                seen.add(k)
                keys.append(k)

    if args.columns:
        keys = [c.strip() for c in args.columns.split(",") if c.strip()]
        for fr in flat_rows:
            if any(k not in fr for k in keys):
                ragged += 1
                break

    # Ragged = rows missing at least one column.
    for fr in flat_rows:
        if any(k not in fr for k in keys):
            ragged += 1
    if ragged:
        log(f"warning: {ragged}/{len(flat_rows)} rows missing one or more columns", args.quiet)

    def cell(v):
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return v

    out = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        w = csv.writer(out, delimiter=args.delimiter)
        w.writerow(keys)
        for fr in flat_rows:
            w.writerow([cell(fr.get(k)) for k in keys])
    finally:
        if args.output:
            out.close()

    log(f"wrote {len(flat_rows)} rows x {len(keys)} columns", args.quiet)
    if args.strict and (errors or ragged):
        return 1
    return 0


def load_records_from_text(text):
    """Parse records from a text blob (used for stdin)."""
    errors = []
    stripped = text.strip()
    if not stripped:
        return [], ["empty input"]
    try:
        doc = json.loads(stripped)
        if isinstance(doc, list):
            return [r for r in doc if isinstance(r, dict)], errors
        if isinstance(doc, dict):
            for k in ("data", "items", "results", "rows", "records"):
                if isinstance(doc.get(k), list):
                    return [r for r in doc[k] if isinstance(r, dict)], errors
            return [doc], errors
    except json.JSONDecodeError:
        pass
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON ({e.msg})")
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            errors.append(f"line {i}: not a JSON object")
    return rows, errors


if __name__ == "__main__":
    sys.exit(main())
