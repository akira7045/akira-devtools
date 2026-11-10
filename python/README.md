# akira-devtools (Python package)

`pip install`-able packaging for the seven zero-dependency tools in this repo:
`secretscan`, `apidiff`, `jsonl2csv`, `dupfind`, `envcheck`, `logsum`, `ga4merge`.

All tools are pure standard-library Python 3.8+. Installing exposes each tool as
its own command, plus a unified `akira-devtools <tool>` dispatcher.

## Install (from this directory)

```bash
pip install .
```

Or build a wheel and install it:

```bash
python3 -m pip install build
python3 -m build --wheel
pip install dist/akira_devtools-1.0.0-py3-none-any.whl
```

## Commands

```bash
secretscan .                    # scan for secrets (exit 1 if findings)
logsum access.log --by status   # summarize logs
ga4merge a.csv b.csv -o merged.csv  # merge GA4 CSV exports
jsonl2csv data.jsonl            # JSON/JSONL -> CSV
dupfind ~/projects              # find duplicate files
apidiff diff old.json new.json  # diff API responses
envcheck .env --example .env.example   # validate env files

akira-devtools --help           # list all tools
```

## Verify

Each tool keeps its single-file test suite in its product directory
(`../secretscan/test_secretscan.py`, etc.); all 177 tool tests pass, plus 10
tests for this package (`python3 test_devtools_package.py`). See
`../compatibility.md` for the per-Python-version matrix.

## License

MIT
