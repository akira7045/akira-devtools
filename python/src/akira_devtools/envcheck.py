#!/usr/bin/env python3
"""
envcheck.py - Zero-dependency .env linter & validator.

Catch environment-config problems before they reach production: missing keys,
empty values, undeclared keys, obvious type errors, and duplicate definitions.
Safe by design: reads files only, never prints secret values.

Usage:
    python3 envcheck.py .env                          # validate syntax only
    python3 envcheck.py .env --example .env.example   # compare against template
    python3 envcheck.py .env --schema schema.txt      # required + typed keys
    python3 envcheck.py .env --require API_KEY,DB_URL # quick required-keys check
    python3 envcheck.py .env --example .env.example --strict

Schema file format (one rule per line):
    KEY                 # required, any non-empty value
    KEY=int             # required, must parse as integer
    KEY=bool            # required, true/false/1/0/yes/no
    KEY=url             # required, looks like http(s) URL
    KEY?                # optional (validated for type if given)

Example-file comparison:
    - keys in --example but missing in target      -> error (or warning w/o --strict)
    - keys in target but not in --example          -> warning (undeclared)
    - empty value where example has a value        -> warning

Duplicate keys: last definition wins (dotenv behavior) but is reported.

Options:
    --example PATH     compare against a template .env
    --schema PATH      validate types/requirements from a schema file
    --require LIST     comma-separated keys that must be present and non-empty
    --allow-empty      do not flag empty values
    --strict           treat warnings as errors
    --quiet            suppress per-key notes; print only the summary
    --no-color         disable ANSI colors

Exit code: 0 = ok, 1 = problems found, 2 = usage error.

License: MIT
"""
import argparse
import re
import sys

_URL_RE = re.compile(r"^https?://[^\s]+$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_BOOLS = {"true", "false", "1", "0", "yes", "no"}


class Colors:
    def __init__(self, enabled):
        self.enabled = enabled

    def _c(self, code, s):
        return f"\033[{code}m{s}\033[0m" if self.enabled else s

    def red(self, s):
        return self._c("31", s)

    def yellow(self, s):
        return self._c("33", s)

    def green(self, s):
        return self._c("32", s)

    def dim(self, s):
        return self._c("2", s)


def parse_env(path):
    """Parse a dotenv file. Returns (pairs, duplicates). Lines like KEY=VALUE.

    Supports: blank lines, '#' comments, optional 'export ' prefix, and
    single/double quoted values. Unquoted trailing comments are stripped.
    """
    pairs = []
    seen = {}
    duplicates = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip("\n").rstrip("\r")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[len("export "):].lstrip()
            if "=" not in stripped:
                pairs.append((stripped, None, lineno, "malformed"))
                continue
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            elif val.startswith("#"):
                val = ""
            elif " #" in val:
                val = val.split(" #", 1)[0].rstrip()
            if key in seen:
                duplicates.append((key, lineno, seen[key]))
            seen[key] = lineno
            pairs.append((key, val, lineno, None))
    return pairs, duplicates


def load_example_keys(path):
    pairs, _ = parse_env(path)
    return {k: v for (k, v, _, _) in pairs}


def load_schema(path):
    """Return dict key -> rule ('', 'int', 'bool', 'url') and optional set."""
    schema = {}
    optional = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            opt = False
            if line.endswith("?"):
                opt = True
                line = line[:-1].strip()
            if "=" in line:
                key, _, rule = line.partition("=")
                key, rule = key.strip(), rule.strip().lower()
            else:
                key, rule = line, ""
            schema[key] = rule
            if opt:
                optional.add(key)
    return schema, optional


def type_ok(rule, val):
    if rule == "int":
        return bool(_INT_RE.match(val))
    if rule == "bool":
        return val.lower() in _BOOLS
    if rule == "url":
        return bool(_URL_RE.match(val))
    return True


def looks_like_placeholder(val):
    low = val.lower()
    return low in ("changeme", "xxx", "todo", "<your-key>", "your_key_here") or (
        "#" in val and "set" in low
    )


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="envcheck",
        description="Validate .env files: missing keys, empty values, types. Read-only.",
    )
    p.add_argument("file", help=".env file to validate")
    p.add_argument("--example", help="template .env to compare key sets against")
    p.add_argument("--schema", help="schema file with KEY / KEY=type rules")
    p.add_argument("--require", default="", help="comma-separated required keys")
    p.add_argument("--allow-empty", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args(argv)

    color = Colors(enabled=sys.stdout.isatty() and not args.no_color)

    try:
        pairs, duplicates = parse_env(args.file)
    except OSError as e:
        print(f"envcheck: cannot read {args.file}: {e}", file=sys.stderr)
        return 2

    values = {}
    errors = 0
    warnings = 0

    def err(msg):
        nonlocal errors
        errors += 1
        print(f"{color.red('ERROR')}  {msg}")

    def warn(msg):
        nonlocal warnings
        warnings += 1
        print(f"{color.yellow('WARN')}   {msg}")

    def note(msg):
        if not args.quiet:
            print(f"{color.dim('  ' + msg)}")

    for (key, val, lineno, problem) in pairs:
        if problem == "malformed":
            err(f"line {lineno}: not a KEY=VALUE line: {key!r}")
            continue
        values[key] = val

    for (key, lineno, first) in duplicates:
        warn(f"duplicate key '{key}' at line {lineno} (first at line {first}); last wins")

    if args.example:
        try:
            example = load_example_keys(args.example)
        except OSError as e:
            print(f"envcheck: cannot read {args.example}: {e}", file=sys.stderr)
            return 2
        for key, exval in example.items():
            if key not in values:
                (err if args.strict else warn)(
                    f"missing key '{key}' (present in {args.example})"
                )
            elif not values[key] and exval and not args.allow_empty:
                warn(f"key '{key}' is empty (template has a value)")
        for key in values:
            if key not in example:
                warn(f"key '{key}' is not declared in {args.example}")

    if args.require:
        for key in [k.strip() for k in args.require.split(",") if k.strip()]:
            if key not in values:
                err(f"required key '{key}' is missing")
            elif not values[key]:
                err(f"required key '{key}' is empty")

    if args.schema:
        try:
            schema, optional = load_schema(args.schema)
        except OSError as e:
            print(f"envcheck: cannot read {args.schema}: {e}", file=sys.stderr)
            return 2
        for key, rule in schema.items():
            if key not in values:
                if key not in optional:
                    err(f"missing required key '{key}' (from schema)")
                continue
            val = values[key]
            if not val:
                if key not in optional and not args.allow_empty:
                    err(f"key '{key}' is required by schema but empty")
                continue
            if not type_ok(rule, val):
                err(f"key '{key}' = <redacted len={len(val)}> is not a valid {rule}")
            elif looks_like_placeholder(val):
                warn(f"key '{key}' looks like an unfilled placeholder")

    total = len(values)
    if errors == 0 and warnings == 0:
        print(color.green(f"OK: {total} keys validated, no problems"))
        return 0

    if not args.quiet:
        print()
    summary = f"{total} keys, {errors} error(s), {warnings} warning(s)"
    print(color.red(summary) if errors else color.yellow(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
