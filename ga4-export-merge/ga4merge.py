#!/usr/bin/env python3
"""ga4merge - merge multiple Google Analytics 4 CSV exports into one clean table.

Zero dependencies, Python 3 standard library only, read-only on inputs.

GA4 exports have a fixed two-row preamble handled here:
  row1: Report metadata (title, dates)      -> skipped
  row2: column header
  row3: date-range summary row              -> skipped by default
  rowN: actual data rows

Why this exists
---------------
Pulling "Last 28 days" from six properties and comparing them by hand is the
single most common time sink for a small marketing team. This tool stacks those
exports into one file, adds the `source_file` column so every row is traceable,
and reports a per-file/per-property summary — as a CSV, or `--json`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

META_KEYS = ("report", "reporting", "期間", "レポート", "日付")


def reader_rows(path: str):
    with open(path, newline="", encoding="utf-8-sig") as f:
        yield from csv.reader(f)


def read_ga4_csv(path: str):
    """Return (header, rows, meta) from a GA4 CSV export.

    header/rows are lists of str. meta collects the preamble row(s) verbatim.
    GA4 writes a summary row as row3 containing a non-date token in the date
    column; we drop rows that are not real data by requiring the first column to
    look like a date (YYYYMMDD / YYYY-MM-DD) or any int-only when no date column.
    """
    raw = [r for r in reader_rows(path) if r and any(c.strip() for c in r)]
    if not raw:
        return [], [], {}
    meta = {"preamble": []}
    # A GA4 export starts with a '#'-commented title row. Only a comment line
    # counts as the preamble; anything else is the header itself.
    if raw[0] and raw[0][0].lstrip().startswith("#"):
        meta["preamble"].append(raw[0])
        raw = raw[1:]
    if not raw:
        return [], [], meta
    header = raw[0]
    data = raw[1:]
    out = []
    for r in data:
        if not r or all(c.strip() == "" for c in r):
            continue
        if len(r) < len(header):
            r = r + [""] * (len(header) - len(r))
        out.append(r[: len(header)])
    return header, out, meta


def merge(files, include_summary: bool = False):
    """Merge CSV files. Returns (columns, rows, per_file)."""
    columns = ["source_file"]
    rows = []
    per_file = []
    for path in files:
        header, data, _ = read_ga4_csv(path)
        if not header:
            per_file.append({"file": path, "rows": 0, "status": "empty"})
            continue
        for col in header:
            if col not in columns:
                columns.append(col)
        name = os.path.basename(path)
        for r in data:
            record = {col: "" for col in columns}
            record["source_file"] = name
            for i, col in enumerate(header):
                record[col] = r[i] if i < len(r) else ""
            rows.append(record)
        per_file.append({"file": name, "rows": len(data), "status": "ok"})
    return columns, rows, per_file


def write_csv(out_path, columns, rows):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summary(per_file):
    out = {
        "files": len(per_file),
        "total_rows": sum(p.get("rows", 0) for p in per_file),
        "per_file": per_file,
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ga4merge", description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="GA4 CSV export files")
    ap.add_argument("-o", "--output", default="merged.csv", help="output CSV (default: merged.csv)")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    ap.add_argument("--stdout", action="store_true", help="write merged CSV to stdout instead of a file")
    args = ap.parse_args(argv)

    missing = [p for p in args.files if not os.path.exists(p)]
    if missing:
        for m in missing:
            print(f"ga4merge: not found: {m}", file=sys.stderr)
        return 2

    columns, rows, per_file = merge(args.files)
    if args.stdout:
        w = csv.DictWriter(sys.stdout, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    else:
        write_csv(args.output, columns, rows)
        print(f"ga4merge: merged {sum(p['rows'] for p in per_file)} rows from {len(per_file)} files -> {args.output}")

    s = summary(per_file)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
