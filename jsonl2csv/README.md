# jsonl2csv

Zero-dependency JSON / JSONL to CSV converter with built-in data-quality checks.

Turn messy logs, exports, and API dumps into clean CSV — no install, no cloud,
no account. Single file, pure Python 3 standard library.

## Why

Most JSON-to-CSV tools either need `pandas` (heavy), choke on ragged records,
or silently drop nested data. `jsonl2csv` handles all three:

- **Ragged records** — rows with missing keys become empty cells, and it tells you
  how many rows were ragged.
- **Nested objects** — flattened to dotted columns (`user.name`, `user.id`).
- **Arrays** — preserved as JSON text (valid CSV, lossless).
- **Bad lines** — invalid JSONL lines are reported on stderr, not silently skipped.
- **Wrapped payloads** — automatically unpacks `{"data": [...]}`, `{"items": [...]}`,
  `{"results": [...]}`, etc.

## Usage

```bash
# JSONL or JSON array -> CSV on stdout
python3 jsonl2csv.py data.jsonl > data.csv

# Write to a file, semicolon delimiter
python3 jsonl2csv.py data.json -o data.csv --delimiter ';'

# Read from stdin
cat data.jsonl | python3 jsonl2csv.py -

# Force column order / subset
python3 jsonl2csv.py data.json --columns id,name,email

# Keep nested values as JSON text instead of flattening
python3 jsonl2csv.py data.json --no-flatten

# CI mode: fail (exit 1) if any row is ragged or any line is invalid
python3 jsonl2csv.py data.jsonl --strict
```

## Options

| Flag | Description |
|------|-------------|
| `-o, --output PATH` | Write CSV to PATH instead of stdout |
| `--delimiter CHAR`  | CSV delimiter (default `,`) |
| `--no-flatten`      | Keep nested objects/arrays as JSON text |
| `--columns LIST`    | Comma-separated column order (subset or reorder) |
| `--strict`          | Exit 1 if any row is ragged or has a parse error |
| `--quiet`           | Suppress stderr warnings |

## Exit codes

- `0` — success
- `1` — no valid records, or `--strict` found problems
- `2` — usage error

## Examples

Input `events.jsonl`:
```json
{"id":1,"user":{"name":"ann","tags":["a","b"]},"score":9.5}
{"id":2,"user":{"name":"bob"},"score":null}
{"id":3,"extra":true}
```

Output:
```
id,user.name,user.tags,score,extra
1,ann,"[""a"", ""b""]",9.5,
2,bob,,,
3,,,,True
```
```
warning: 3/3 rows missing one or more columns
wrote 3 rows x 5 columns
```

## Tests

```bash
python3 test_jsonl2csv.py
# 13/13 passed
```

Covers: JSONL, JSON array, wrapped payloads, ragged rows, nested flattening,
no-flatten, column order/subset, custom delimiter, file output, invalid-line
reporting, strict mode, stdin, empty input.

## License

MIT — see LICENSE.
