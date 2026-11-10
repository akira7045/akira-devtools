# ga4merge

Merge several Google Analytics 4 CSV exports into one clean, traceable table —
without loading a log platform, a spreadsheet macro, or `pip install` anything.
Pure Python 3 standard library. Read-only on your inputs.

## Why

If you run more than one GA4 property (or export sessions, conversions and
landing-page reports separately) the "Last 28 days" numbers live in several CSV
files. Comparing them by hand means copy-paste, mis-aligned columns, and losing
track of which row came from which export.

`ga4merge` stacks those exports into one CSV, adds a `source_file` column so
every row is traceable, unions the columns of all files, and prints a per-file
row-count summary (or `--json` for a pipeline).

## What it handles for you

- GA4's export preamble (the `# Report title` line and the summary row) is
  skipped automatically.
- Different reports can have different columns — the output is the union, with
  blanks where a file lacks a column.
- BOM-prefixed CSVs from Excel are read correctly.
- Short/ragged rows are padded, never crash the merge.
- A file with no data rows is reported as `empty` instead of silently vanishing.

## Usage

```bash
python3 ga4merge.py a.csv b.csv -o merged.csv
python3 ga4merge.py exports/*.csv --json          # per-file row counts as JSON
python3 ga4merge.py a.csv --stdout > merged.csv   # pipe-friendly
```

Example output:

```
ga4merge: merged 4 rows from 2 files -> merged.csv
```

Exit codes: `0` ok, `2` an input file was missing.

## Test

```bash
python3 test_ga4merge.py
```

8 tests, plain `unittest`, no dependencies.

## License

MIT — see LICENSE.
