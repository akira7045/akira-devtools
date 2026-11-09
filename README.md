# AKIRA Dev Tools Bundle

Six single-file, dependency-free Python 3 CLI tools. Each ships with a test
suite. No third-party packages required — just Python 3.8+.

| Tool | Purpose | Tests |
|------|---------|-------|
| `apidiff`   | Diff API responses vs a stored baseline (contract drift) | 48/48 |
| `secretscan`| Scan a repo for hardcoded secrets before you commit    | 13/13 |
| `jsonl2csv` | Convert JSON / JSONL to CSV with field control         | 13/13 |
| `dupfind`   | Find duplicate files by hash (read-only, never deletes)| 18/18 |
| `envcheck`  | Lint a `.env` against a template/schema (never prints secrets) | 30/30 |
| `logsum`    | Summarize access/syslog/JSONL logs into counts (read-only) | 13/13 |

Read the write-up: **[Catching API contract drift in CI](docs/catching-api-contract-drift-in-ci.md)** — a worked example using `apidiff`, with real command output.

Try everything in one command, zero setup: `bash demo.sh`
(creates a throwaway temp dir, feeds each tool sample input, cleans up after itself).

## Why these
- **Single file** — copy one `.py` into your project, done.
- **Stdlib only** — no pip, no virtualenv, no supply-chain risk.
- **Tested** — 135 tests across the six tools, all passing.
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
  python/      pip-installable packaging (pyproject.toml, console scripts)
```

Each tool is licensed under the terms in its own `LICENSE` file.
