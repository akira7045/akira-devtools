# apidiff

Zero-dependency API response differ. Capture a baseline from any HTTP endpoint,
then diff the live response against it to catch breaking changes.

Single file, pure Python 3 standard library. No install, no cloud, no account.

## Use cases

- Detect breaking changes in third-party APIs you depend on (schema drift).
- Guard a production endpoint's response shape in CI.
- Compare staging vs production payloads.
- Snapshot a JSON endpoint and alert when it changes.

## Usage

### Capture a baseline

```bash
python3 apidiff.py save https://api.example.com/v1/status baseline.json
```

### Check for drift

```bash
python3 apidiff.py check https://api.example.com/v1/status baseline.json
# exit 0 = identical, 1 = differences, 2 = request/parse error
```

### Diff two local files

```bash
python3 apidiff.py diff old.json new.json
```

### Auth and POST

```bash
python3 apidiff.py check https://api.example.com/v1/me me.json \
  --header "Authorization: Bearer $TOKEN"
```

```bash
python3 apidiff.py save https://api.example.com/v1/query base.json \
  --data '{"q":"hello"}'          # implies POST
```

### Machine-readable output

```bash
python3 apidiff.py check URL baseline.json --json
```

## Output

```
[removed] user.email
    - "a@example.com"
    + "<missing>"
[changed] version
    - "1.2.0"
    + "1.3.0"
[added  ] metadata.region
    - "<missing>"
    + "eu-west-1"
```

Nested objects/arrays are walked recursively; array length changes are reported.

## Breaking vs non-breaking changes

By default every difference is reported. Use `--breaking-only` to surface
only the changes that can break an existing consumer: removed keys, type
changes, and array length changes. Purely additive changes (new keys) are
suppressed, which is handy for CI gates where you care about regressions, not
new fields.

```bash
python3 apidiff.py check "$API_URL" contract.json --breaking-only
```

## CI example

```bash
python3 apidiff.py check "$API_URL" contract.json --breaking-only || exit 1
```

## Options

| Option | Description |
|---|---|
| `--method GET\|POST` | HTTP method (default GET) |
| `--header "K: V"` | Extra header, repeatable |
| `--data '<json>'` | Request body (implies POST) |
| `--timeout SECONDS` | Request timeout (default 15) |
| `--json` | Emit diff as JSON |
| `--breaking-only` | Report only breaking changes (removed/type/length) |

## Run the tests

```bash
python3 test_apidiff.py   # 48/48, uses a local HTTP server, no network needed
```

## License

MIT. See LICENSE.
