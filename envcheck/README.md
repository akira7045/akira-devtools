# envcheck

Zero-dependency `.env` linter & validator. Catch environment-config problems
before they reach production: missing keys, empty values, undeclared keys,
obvious type errors, and duplicate definitions.

Safe by design: it reads files only and **never prints secret values** — only
lengths (`<redacted len=9>`). Drop it into a pre-commit hook or CI to stop a
broken `.env` from shipping.

## Why

A typo'd `.env` is one of the most common causes of a "works on my machine"
outage: an empty API key, a `PORT=eight-thousand`, a key that was in
`.env.example` but never copied over. `envcheck` is a single file, pure Python 3
standard library — no pip install, no SaaS, no config to learn.

## Usage

```bash
python3 envcheck.py .env                           # validate syntax only
python3 envcheck.py .env --example .env.example    # compare against a template
python3 envcheck.py .env --schema schema.txt       # required + typed keys
python3 envcheck.py .env --require API_KEY,DB_URL  # quick required-keys check
python3 envcheck.py .env --example .env.example --strict
python3 envcheck.py --predeploy .env --example .env.example --schema schema.txt --out ci-report.txt
```

Exit code is `0` when clean, `1` when problems are found, `2` on usage error —
ideal for CI gating. `--strict` turns warnings into errors.

### Deploy gate mode

`--predeploy` is the one-flag CI gate: it implies `--strict`, prints a final
`RESULT: PASS` / `RESULT: FAIL` line, and exits **2** on any problem (errors
*or* warnings) so a broken `.env` can never reach production. Add `--out PATH`
to write the same plain-text (no-ANSI) report to a file for build artifacts or
PR comments.

```bash
python3 envcheck.py --predeploy .env --example .env.example --schema schema.txt --out ci-report.txt
# exit 0 -> deploy;  exit 2 -> block the deploy
```

### Schema file

One rule per line:

```
KEY                 # required, any non-empty value
KEY=int             # required, must parse as an integer
KEY=bool            # required, true/false/1/0/yes/no
KEY=url             # required, looks like http(s) URL
KEY?                # optional (type-checked if given)
```

### Options

| Flag | Meaning |
|------|---------|
| `--example PATH` | Compare against a template `.env` |
| `--schema PATH` | Validate types/requirements from a schema file |
| `--require LIST` | Comma-separated keys that must be present and non-empty |
| `--allow-empty` | Do not flag empty values |
| `--strict` | Treat warnings as errors |
| `--quiet` | Print only the summary |
| `--no-color` | Disable ANSI colors |
| `--predeploy` | CI/deploy gate: warnings are errors, exit `2` on failure, `RESULT: PASS/FAIL` line |
| `--out PATH` | Write a plain-text report to `PATH` |

## Real output

Schema (`schema.txt`):

```
API_KEY
DB_URL=url
PORT=int
```

Broken `.env`:

```
API_KEY=
DB_URL=not-a-url
PORT=abc
DUP=1
DUP=2
```

```
$ python3 envcheck.py .env --schema schema.txt
WARN   duplicate key 'DUP' at line 5 (first at line 4); last wins
ERROR  key 'API_KEY' is required by schema but empty
ERROR  key 'DB_URL' = <redacted len=9> is not a valid url
ERROR  key 'PORT' = <redacted len=3> is not a valid int

4 keys, 3 error(s), 1 warning(s)
$ echo $?
1
```

Clean `.env`, same schema:

```
$ python3 envcheck.py .env --schema schema.txt
OK: 3 keys validated, no problems
$ echo $?
0
```

Compare against a template:

```
$ python3 envcheck.py .env --example .env.example
WARN   missing key 'NEW_KEY' (present in .env.example)
WARN   key 'PORT' is not declared in .env.example

3 keys, 0 error(s), 2 warning(s)
```

## Pre-commit hook

```bash
#!/bin/sh
python3 path/to/envcheck.py .env --example .env.example --strict \
  || { echo "Broken .env, commit blocked."; exit 1; }
```

## Install

No install needed. Copy `envcheck.py` anywhere and run it with Python 3.7+.

## Tests

```bash
python3 test_envcheck.py    # 30/30 passed
```

## License

MIT. See LICENSE.
