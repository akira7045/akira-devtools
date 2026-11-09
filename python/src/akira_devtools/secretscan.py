#!/usr/bin/env python3
"""
secretscan.py - Zero-dependency secret scanner for git repositories and directories.

Detects common credential patterns (AWS keys, private keys, API tokens, passwords
in config, etc.) with context, entropy analysis, and a clean report.

Usage:
    python3 secretscan.py [PATH]            # scan a directory (default: .)
    python3 secretscan.py --json PATH       # machine-readable output
    python3 secretscan.py --max-entropy N   # entropy floor for generic matches (default 2.0)

Exit code: 1 if findings, 0 if clean. Suitable for pre-commit hooks / CI.

License: MIT
"""
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".mypy_cache"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".exe", ".so", ".dll", ".woff", ".woff2", ".ico", ".mp4", ".mp3"}
MAX_FILE_BYTES = 2_000_000

PATTERNS = [
    ("aws_access_key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws.{0,20}(secret|access).{0,20}['\"]([A-Za-z0-9/+=]{40})['\"]")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("stripe_key", re.compile(r"\b(sk|rk)_(live|test)_[0-9A-Za-z]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("generic_password", re.compile(r"(?i)(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]")),
    ("generic_assignment", re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]([^'\"\s]{12,})['\"]")),
]

PLACEHOLDER_HINTS = re.compile(r"(?i)(example|sample|dummy|placeholder|xxxx|<.*?>|your[_-]|changeme|redacted|test_key|fake)")


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    n = len(s)
    return -sum((ct / n) * math.log2(ct / n) for ct in counts.values())


def scan_line(line: str, max_entropy: float):
    hits = []
    for name, pat in PATTERNS:
        for m in pat.finditer(line):
            snippet = m.group(0)
            if PLACEHOLDER_HINTS.search(snippet):
                continue
            value = m.group(m.lastindex) if m.lastindex else snippet
            ent = shannon_entropy(value)
            if name.startswith("generic") and ent < max_entropy:
                continue
            hits.append((name, snippet[:120], round(ent, 2)))
    return hits


def scan_file(path: Path, max_entropy: float):
    results = []
    try:
        data = path.read_text(errors="ignore")
    except Exception:
        return results
    for ln, line in enumerate(data.splitlines(), 1):
        for name, snippet, ent in scan_line(line, max_entropy):
            results.append({"file": str(path), "line": ln, "type": name, "match": snippet, "entropy": ent})
    return results


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in BINARY_EXT:
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def main():
    ap = argparse.ArgumentParser(description="Zero-dependency secret scanner.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-entropy", type=float, default=2.0,
                    help="minimum entropy for generic password/key matches (default 2.0)")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"path not found: {root}", file=sys.stderr)
        return 2

    findings = []
    for f in iter_files(root):
        findings.extend(scan_file(f, args.max_entropy))

    if args.json:
        print(json.dumps({"findings": findings, "count": len(findings)}, indent=2))
    else:
        if not findings:
            print("No secrets detected. Clean.")
        else:
            print(f"Found {len(findings)} potential secret(s):\n")
            for f in findings:
                print(f"  [{f['type']}] {f['file']}:{f['line']}  (entropy={f['entropy']})")
                print(f"      {f['match']}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
