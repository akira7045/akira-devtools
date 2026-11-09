---
title: "Catching API contract drift in CI (no dependencies, no account)"
published: false
description: "Gate your build on breaking third-party API changes with one stdlib-only file and four lines of CI. No SaaS, no account."
tags: python, api, devops, testing
canonical_url: https://github.com/akira7045/akira-devtools/blob/main/docs/catching-api-contract-drift-in-ci.md
cover_image: https://raw.githubusercontent.com/akira7045/akira-devtools/main/covers/apidiff.png
---

Third-party APIs change without telling you. A field is renamed, a type flips
from number to string, an array loses an element. Your integration keeps
running until the exact moment it doesn't — usually in production, on a Friday.

You don't need a SaaS contract-monitoring service to catch this. You need one
snapshot of a known-good response, one command in CI, and an exit code. This
post shows a ~200-line, standard-library-only tool called `apidiff` that does
exactly that. All output below is real, run on 2026-11-09.

## The idea

1. Save a baseline: the response body you know is correct.
2. On every run, fetch the live response and diff it against the baseline.
3. Fail the build only on **breaking** changes (removed keys, type changes,
   array length changes). Ignore harmless additions.

That last point matters. Most "diff" tools are too noisy: a new field added by
the vendor is not a reason to page someone. You want to gate on regressions,
not on every byte.

## Install

No pip, no account. Copy one file:

```bash
git clone https://github.com/akira7045/akira-devtools
cp akira-devtools/apidiff/apidiff.py .
```

Python 3.8+, standard library only.

## Capture a baseline

```bash
python3 apidiff.py save https://api.example.com/v1/status baseline.json
```

## Diff two payloads

Say your service used to return this (what you built against):

```json
{"version":"1.2.0","user":{},"metadata":{}}
```

…and today the vendor returns this:

```json
{"version":"1.3.0","user":{"email":"a@example.com"},"metadata":{"region":"eu-west-1"}}
```

Full diff:

```bash
python3 apidiff.py diff old.json new.json
```

```
[added  ] metadata.region
    - "<missing>"
    + "eu-west-1"
[added  ] user.email
    - "<missing>"
    + "a@example.com"
[changed] version
    - "1.2.0"
    + "1.3.0"
```

Three changes. Only one — the `version` change — is the kind that can break a
consumer that pins on it. The two new keys are additive and safe.

## Gate on breaking changes only

```bash
python3 apidiff.py diff old.json new.json --breaking-only
```

```
[changed] version
    - "1.2.0"
    + "1.3.0"
```

Exit code `1` because a real change was found. The additive keys are suppressed.

## Put it in CI

```yaml
# .github/workflows/contract.yml
- name: Check API contract
  run: |
    python3 apidiff.py check "$API_URL" contract.json --breaking-only
```

`check` exits `0` (identical / only additive), `1` (breaking change), or `2`
(request/parse error). No external service, no secrets beyond the API itself.

## Auth and POST endpoints

```bash
python3 apidiff.py save https://api.example.com/v1/query base.json \
  --data '{"q":"hello"}'            # implies POST

python3 apidiff.py check https://api.example.com/v1/me me.json \
  --header "Authorization: Bearer $TOKEN"
```

## Machine-readable output

```bash
python3 apidiff.py check "$API_URL" contract.json --json
```

Pipe it into your PR commenter, Slack notifier, or whatever you already have.

## Why not a hosted service?

Hosted contract monitoring is great — if you have the budget and the data
leaves your network without an argument. For a single internal dependency, a
snapshot file in your repo plus four lines of CI is enough, costs nothing,
and keeps your payloads local. `apidiff` is that minimal version.

It carries 48 tests (local HTTP server, no network needed) and ships alongside
five other single-file tools: `secretscan`, `jsonl2csv`, `dupfind`, `envcheck`,
`logsum`.

- **Free**: the code is MIT-licensed on GitHub. Use it, fork it, ship it.
- **Paid (for teams that need it)**: a commercial license with a 30-day
  bug-fix window and a named support contact — the things a company's
  procurement actually asks for that MIT doesn't provide.
  Buy at a fixed price: https://15roh.gumroad.com/l/apidiff-commercial

Repo: https://github.com/akira7045/akira-devtools
