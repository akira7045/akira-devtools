# Compatibility: runtime-verified on Python 3.8 – 3.12

"Just Python 3.8+" is easy to claim and easy to get wrong. This page records
what we actually ran, on which interpreters, with what result. Nothing here is
inferred from reading the source — every row below is a command that was
executed and an exit code that was observed.

Measured 2026-11-11.

## Interpreters

| Version | How installed |
|---------|---------------|
| 3.8.18  | built from source (pyenv) |
| 3.9.19  | built from source (pyenv) |
| 3.10.15 | built from source (pyenv) |
| 3.11.11 | built from source (pyenv) |
| 3.12.3  | system interpreter |

## Result: `bash demo.sh`

The one-command demo (`demo.sh`) runs all seven tools against sample input in a
throwaway temp dir. Expected: exit 0 on every version.

| Version | demo.sh exit |
|---------|--------------|
| 3.8.18  | 0 |
| 3.9.19  | 0 |
| 3.10.15 | 0 |
| 3.11.11 | 0 |
| 3.12.3  | 0 |

## Result: per-tool test suites

Each tool ships a self-contained runner. Expected: exit 0 and the full count on
every version.

| Tool          | Tests | 3.8 | 3.9 | 3.10 | 3.11 | 3.12 |
|---------------|------:|:---:|:---:|:----:|:----:|:----:|
| apidiff       | 48    | ok  | ok  | ok   | ok   | ok   |
| secretscan    | 35    | ok  | ok  | ok   | ok   | ok   |
| envcheck      | 42    | ok  | ok  | ok   | ok   | ok   |
| dupfind       | 18    | ok  | ok  | ok   | ok   | ok   |
| jsonl2csv     | 13    | ok  | ok  | ok   | ok   | ok   |
| logsum        | 13    | ok  | ok  | ok   | ok   | ok   |
| ga4merge      | 8     | ok  | ok  | ok   | ok   | ok   |
| **total**     | **177** | ok | ok | ok   | ok   | ok   |

All 177 tests pass on all five interpreters (885 test-executions, zero
failures).

## How to reproduce

```bash
# extract the delivered tarball into a throwaway dir
tar -xzf akira-devtools-<stamp>.tar.gz -C /tmp/compat && cd /tmp/compat

# with the interpreter you want to check on PATH:
bash demo.sh                          # expect exit 0

for t in apidiff dupfind envcheck jsonl2csv logsum secretscan ga4-export-merge; do
  tf=test_$t.py; [ "$t" = ga4-export-merge ] && tf=test_ga4merge.py
  ( cd "$t" && python3 "$tf" ) || echo "FAILED: $t"
done
```

To check a different interpreter, put that interpreter's `bin` first on
`PATH` and repeat. If any version fails, that is a bug — tell us the version
and the failing tool.

## Scope note

- Verified: CPython on Linux x86_64. Not verified: macOS, Windows, or PyPy
  (expected to work — pure stdlib, no C extensions — but not claimed as tested).
- These are the versions we could stand up on this machine. If your platform
  pin is 3.8 and you depend on it, the tarball you receive is the same one the
  matrix above was run against.
