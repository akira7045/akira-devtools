# poc-registry — idempotent bulk-registration reference

A small, dependency-free, **runnable** reference for the architecture we use on
bulk product-registration jobs (e.g. Yahoo! Shopping / marketplace bulk listing):

```
CSV/DB ──normalize──▶ Product ──idempotent worker (retry/backoff)──▶ transport (API)
                                    │
                                    └── structured JSON report (failures re-run by SKU)
```

Most bulk-registration projects fail in production for the same four reasons —
no exception handling, no retry, no idempotency, no per-item log. This
reference models all four from the start.

## What it guarantees
- **Normalization + validation**: bad rows (empty SKU, non-integer or negative
  price/stock, missing columns) are rejected *before* anything is sent.
- **Idempotency**: each product gets a stable SHA-256 key. A key that already
  succeeded is never sent twice, so retries and re-runs don't create duplicates.
- **Retry with exponential backoff**: transient transport failures are retried
  up to N attempts; permanent failures are recorded, not silently dropped.
- **Structured report**: a JSON report lists per-item status, attempt count, and
  error. Only failed SKUs need re-running — partial re-execution is the default.

## Run
```bash
python3 registry.py sample-products.csv --report report.json
# exit code 0 = all ok, 1 = at least one failed item
```

## Test
```bash
python3 test_registry.py      # 11 tests, no third-party deps
```

## Wiring to a real API
Replace the placeholder `transport(product)` function in `registry.py` with your
API call. Everything else (validation, idempotency, retry, reporting) stays.
For a marketplace that has no write API, wrap the screen automation in the same
`transport` boundary and keep the rest — the pipeline doesn't care how the item
is submitted, only that the call is idempotent and retryable.

## License
MIT. Part of akira-devtools.
