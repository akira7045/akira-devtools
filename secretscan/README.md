# secretscan

Zero-dependency secret scanner for git repos and directories. Catch leaked
credentials before they hit a public repo or CI log.

## Why

Most secret scanners drag in dozens of dependencies or a SaaS subscription.
`secretscan` is a single file, pure Python 3 standard library. Drop it into any
repo, run it in a pre-commit hook or CI, done.

## Detects

- AWS access keys / secret keys
- RSA / EC / OpenSSH / PGP private keys
- GitHub tokens (`ghp_`, `github_pat_`)
- Slack tokens (`xox[baprs]-`)
- Google API keys (`AIza...`)
- Stripe keys (`sk_live_`, `rk_test_`...)
- OpenAI keys (`sk-...`)
- JWTs
- Generic `password=` / `api_key=` / `token=` assignments (entropy floor, default 2.0)
- Entropy analysis on the captured secret value (not the whole line)

Placeholders like `example`, `dummy`, `changeme`, `xxxx`, `<your-key>` are
ignored automatically, so sample configs don't produce noise.

## Usage

```bash
python3 secretscan.py .                 # scan current dir
python3 secretscan.py --json src/       # machine-readable
python3 secretscan.py --max-entropy 3.0 # raise entropy floor (fewer, higher-confidence)
```

Exit code is `1` when secrets are found, `0` when clean — ideal for CI gating.

### Pre-commit hook

```bash
#!/bin/sh
python3 path/to/secretscan.py . || { echo "Secrets detected, commit blocked."; exit 1; }
```

## Install

No install needed. Copy `secretscan.py` anywhere and run it with Python 3.7+.

## License

MIT. See LICENSE.
