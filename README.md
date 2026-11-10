# AKIRA Dev Tools Bundle

Seven single-file, dependency-free Python 3 CLI tools. Each ships with a test
suite. No third-party packages required — just Python 3.8+.

| Tool | Purpose | Tests |
|------|---------|-------|
| `apidiff`   | Diff API responses vs a stored baseline (contract drift) | 48/48 |
| `secretscan`| Scan a repo for hardcoded secrets before you commit    | 35/35 |
| `jsonl2csv` | Convert JSON / JSONL to CSV with field control         | 13/13 |
| `dupfind`   | Find duplicate files by hash (read-only, never deletes)| 18/18 |
| `envcheck`  | Lint a `.env` against a template/schema (never prints secrets) | 42/42 |
| `logsum`    | Summarize access/syslog/JSONL logs into counts (read-only) | 13/13 |
| `ga4merge`  | Merge multiple GA4 CSV exports (union columns, keep source) | 8/8 |

Read the write-up: **[Catching API contract drift in CI](docs/catching-api-contract-drift-in-ci.md)** — a worked example using `apidiff`, with real command output.

Try everything in one command, zero setup: `bash demo.sh`
(creates a throwaway temp dir, feeds each tool sample input, cleans up after itself).

## Why these
- **Single file** — copy one `.py` into your project, done.
- **Stdlib only** — no pip, no virtualenv, no supply-chain risk.
- **Tested** — all passing: 177 tests across the seven tools plus 9 for the installable package (186 total). Measured 2026-11-11 (run `make test`). Each tool ships its own self-contained runner: `python3 test_<tool>.py` reports the full count. Collection under a test framework varies by tool: `secretscan`, `envcheck`, `logsum`, `ga4merge` are `unittest.TestCase`-based and collect under both `pytest` and `python3 -m unittest`; `apidiff`, `jsonl2csv`, `dupfind` use bare `def test_*` functions that `pytest` collects in full but `unittest` does not — run those three via their own file or `pytest`.
- **Portable** — targets Python 3.8+ (stdlib only). Runtime-verified on **3.8.18, 3.9.19, 3.10.15, 3.11.11 and 3.12.3**: on every version `bash demo.sh` exits 0 (all seven tools run on sample input) and each tool's full test suite passes (177 tests total, 2026-11-11). See `compatibility.md` for the per-version matrix and reproduction steps.
- **Safe** — `dupfind` and `secretscan` never modify or delete your files.

## Honest positioning
These are intentionally small tools. They are **not** meant to replace mature,
feature-rich projects (e.g. gitleaks/trufflehog for secret scanning, jq for
JSON transforms, fdupes/rdfind for duplicate detection). Their niche is:

- you want **one file you can read in a minute**, drop in, and trust;
- you can't or won't install third-party packages (air-gapped, locked-down CI,
  throwaway scripts);
- you want a **read-only, never-deletes** guarantee by design.

If you need deep rule sets or high-volume performance, use the established
tools. If you need "grab one file and go", these are for you.

## Commercial use & support

The code is MIT — free for you to use, modify, and ship, including commercially,
under the MIT terms. No license purchase is required.

If you want more than the MIT grant covers, these are available on request:

- **Commercial support** — a named contact and a 30-day bug-fix window for a
  specific tool or the bundle, instead of "read the source yourself".
- **Setup / CI integration** — I wire a tool into your pipeline and verify it
  against your data.
- **Custom change** — a focused feature or behavior change to one of these tools.

Pricing and scope are agreed per request. To start, **open a GitHub issue titled
`inquiry: <tool or bundle>`** on this repository and describe your use case. I
reply there; no email signup or external account needed.

Fixed-price options for commercial license + 30-day support are also available
to buy directly:

- [apidiff — commercial license + support](https://15roh.gumroad.com/l/apidiff-commercial)
- [secretscan — commercial license + support](https://15roh.gumroad.com/l/secretscan-commercial)
- [dupfind — commercial license + support](https://15roh.gumroad.com/l/dupfind-commercial)
- [jsonl2csv — commercial license + support](https://15roh.gumroad.com/l/jsonl2csv-commercial)
- [envcheck — commercial license + support](https://15roh.gumroad.com/l/envcheck-commercial)
- [logsum — commercial license + support](https://15roh.gumroad.com/l/logsum-commercial)
- [Bundle — all tools + setup + 30-day support](https://15roh.gumroad.com/l/akira-devtools-bundle)

See [SALES.md](SALES.md) for the current option list and indicative pricing.

## Quick start

Download the latest release (single tarball, MIT):
```bash
curl -L -O https://github.com/akira7045/akira-devtools/releases/latest/download/akira-devtools-1.0.0.tar.gz
tar xzf akira-devtools-1.0.0.tar.gz && cd akira-devtools-1.0.0
```

Or clone and run each tool directly — no install step required:
```bash
python3 apidiff/apidiff.py --help
python3 secretscan/secretscan.py --help
python3 jsonl2csv/jsonl2csv.py --help
python3 dupfind/dupfind.py --help
python3 envcheck/envcheck.py --help
python3 logsum/logsum.py --help
python3 ga4-export-merge/ga4merge.py --help
```

### Install as commands (optional)
Symlink all six onto your PATH — no pip, no copying into site-packages:
```bash
./install.sh                 # -> ~/.local/bin
# or:  PREFIX=/usr/local ./install.sh
```
Then just run `apidiff --help`, `secretscan .`, etc.

### Install via pip (optional)
A packaged build lives in `python/`. It exposes each tool as a command plus a
unified `akira-devtools <tool>` dispatcher:
```bash
pip install ./python
akira-devtools --help
```

## Run the tests
```bash
python3 apidiff/test_apidiff.py
python3 secretscan/test_secretscan.py
python3 jsonl2csv/test_jsonl2csv.py
python3 dupfind/test_dupfind.py
python3 envcheck/test_envcheck.py
python3 logsum/test_logsum.py
python3 ga4-export-merge/test_ga4merge.py
```

## Layout
```
products/
  install.sh       symlink the tools onto your PATH
  README.md
  LICENSE
  apidiff/     apidiff.py, test_apidiff.py, README.md, LICENSE
  secretscan/  secretscan.py, test_secretscan.py, README.md, LICENSE
  jsonl2csv/   jsonl2csv.py, test_jsonl2csv.py, README.md, LICENSE
  dupfind/     dupfind.py, test_dupfind.py, README.md, LICENSE
  envcheck/    envcheck.py, test_envcheck.py, README.md, LICENSE
  logsum/      logsum.py, test_logsum.py, README.md, LICENSE
  ga4-export-merge/  ga4merge.py, test_ga4merge.py, README.md, LICENSE
  python/      pip-installable packaging (pyproject.toml, console scripts)
```

Each tool is licensed under the terms in its own `LICENSE` file.
