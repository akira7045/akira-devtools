# logsum

Zero-dependency log summarizer. Point it at a log file (or pipe via stdin) and
get counts grouped by status code, level, app, or any field — without loading a
log platform or installing anything.

## Why

When something breaks, the first useful question is usually "what's the
distribution?" — how many 5xx? how many errors per service? `logsum` answers
that from a single file, pure Python 3 standard library, no pip, no daemon.

## Formats

| `--format` | Handles |
|------------|---------|
| `access`   | Common / Combined Log Format — status, method, path |
| `syslog`   | RFC3164-ish lines — app name |
| `jsonl`    | one JSON object per line — any flat field (`level`, `status`, ...) |
| `auto`     | sniff each line, then a `key=value` fallback (default) |

Only lines that match the format are counted as `matched`; everything else is
still counted in `total`. Read-only — it never writes to your logs.

## Usage

```bash
python3 logsum.py access.log
python3 logsum.py --format access --by status access.log
python3 logsum.py --by level app.jsonl
cat app.log | python3 logsum.py - --by level
python3 logsum.py --top 20 --json app.log
```

Sample output:

```
total lines : 5
matched     : 4
grouped by  : status
  200  2
  404  1
  500  1
```

Exit codes: `0` ok, `1` no lines matched, `2` usage/IO error.

## Field options

`--by` picks the grouping key from the parsed record. Available keys depend on
the format: `access` exposes `status`, `method`, `path`; `syslog` exposes `app`;
`jsonl` exposes any flat top-level field.

## Honest positioning

This is a small, single-purpose tool — not a replacement for a full log
pipeline (jq for arbitrary JSON shaping, awk for ad-hoc scripting, or a real
observability stack for high volume). Its niche: **one readable file**, no
dependencies, works on an air-gapped or locked-down box, safe to run anywhere.

## Tests

```bash
python3 test_logsum.py
```

13 tests, pure `unittest`, no third-party packages.

## License

MIT. See `LICENSE`.
