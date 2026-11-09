#!/usr/bin/env python3
"""Self-contained tests for envcheck. Run: python3 test_envcheck.py"""
import os
import tempfile

import envcheck as e

_fail = 0
_pass = 0


def check(name, cond):
    global _fail, _pass
    if cond:
        _pass += 1
    else:
        _fail += 1
        print(f"FAIL: {name}")


def make(files):
    """files: dict filename -> content. Returns temp dir."""
    d = tempfile.mkdtemp(prefix="envcheck_")
    for name, content in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(content)
    return d


def run(d, *args):
    import io
    import contextlib

    path = os.path.join(d, args[0])
    rest = list(args[1:])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = e.main([path, "--no-color"] + rest)
    return code, buf.getvalue()


def t_parse_basic():
    d = make({".env": "A=1\nB=two\n# comment\n\nexport C=3\n"})
    pairs, dups = e.parse_env(os.path.join(d, ".env"))
    vals = {k: v for (k, v, _, _) in pairs}
    check("parse A", vals.get("A") == "1")
    check("parse B", vals.get("B") == "two")
    check("parse export C", vals.get("C") == "3")
    check("parse no dup", dups == [])


def t_quotes():
    d = make({".env": 'A="hello world"\nB=\'single\'\nC=plain # trailing\n'})
    pairs, _ = e.parse_env(os.path.join(d, ".env"))
    vals = {k: v for (k, v, _, _) in pairs}
    check("double quote stripped", vals.get("A") == "hello world")
    check("single quote stripped", vals.get("B") == "single")
    check("trailing comment stripped", vals.get("C") == "plain")


def t_duplicate():
    d = make({".env": "A=1\nA=2\n"})
    _, dups = e.parse_env(os.path.join(d, ".env"))
    check("duplicate detected", len(dups) == 1 and dups[0][0] == "A")


def t_malformed():
    d = make({".env": "JUSTAWORD\nA=1\n"})
    code, out = run(d, ".env")
    check("malformed -> exit 1", code == 1)
    check("malformed reported", "not a KEY=VALUE" in out)


def t_clean():
    d = make({".env": "A=1\nB=2\n"})
    code, out = run(d, ".env")
    check("clean -> exit 0", code == 0)
    check("clean OK msg", "OK" in out)


def t_require_missing():
    d = make({".env": "A=1\n"})
    code, out = run(d, ".env", "--require", "A,B")
    check("require missing -> exit 1", code == 1)
    check("require missing B reported", "'B'" in out)


def t_require_empty():
    d = make({".env": "A=\n"})
    code, out = run(d, ".env", "--require", "A")
    check("require empty -> exit 1", code == 1)


def t_example_missing():
    d = make({".env": "A=1\n", ".env.example": "A=\nB=\n"})
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"))
    check("example missing non-strict -> exit 0 (warn)", code == 0)
    check("example missing reported", "'B'" in out)


def t_example_missing_strict():
    d = make({".env": "A=1\n", ".env.example": "A=\nB=\n"})
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"), "--strict")
    check("example missing strict -> exit 1", code == 1)


def t_example_undeclared():
    d = make({".env": "A=1\nZ=9\n", ".env.example": "A=\n"})
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"))
    check("undeclared warned", "'Z'" in out)


def t_schema_int():
    d = make({".env": "PORT=abc\n", "s.txt": "PORT=int\n"})
    code, out = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema int bad -> exit 1", code == 1)


def t_schema_int_ok():
    d = make({".env": "PORT=8080\n", "s.txt": "PORT=int\n"})
    code, _ = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema int ok -> exit 0", code == 0)


def t_schema_url():
    d = make({".env": "URL=nope\n", "s.txt": "URL=url\n"})
    code, out = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema url bad -> exit 1", code == 1)
    d2 = make({".env": "URL=https://x.io\n", "s.txt": "URL=url\n"})
    code2, _ = run(d2, ".env", "--schema", os.path.join(d2, "s.txt"))
    check("schema url ok -> exit 0", code2 == 0)


def t_schema_bool():
    d = make({".env": "FLAG=maybe\n", "s.txt": "FLAG=bool\n"})
    code, _ = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema bool bad -> exit 1", code == 1)
    d2 = make({".env": "FLAG=yes\n", "s.txt": "FLAG=bool\n"})
    code2, _ = run(d2, ".env", "--schema", os.path.join(d2, "s.txt"))
    check("schema bool ok -> exit 0", code2 == 0)


def t_schema_optional():
    d = make({".env": "A=1\n", "s.txt": "A=int\nOPT?\n"})
    code, _ = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema optional absent -> exit 0", code == 0)


def t_schema_required_absent():
    d = make({".env": "A=1\n", "s.txt": "A=int\nREQ\n"})
    code, out = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("schema required absent -> exit 1", code == 1)
    check("schema required absent named", "'REQ'" in out)


def t_secret_not_leaked():
    d = make({".env": "TOKEN=supersecretvalue\n", "s.txt": "TOKEN=int\n"})
    code, out = run(d, ".env", "--schema", os.path.join(d, "s.txt"))
    check("secret value not printed", "supersecretvalue" not in out)


def t_allow_empty():
    d = make({".env": "A=\n", ".env.example": "A=x\n"})
    code, _ = run(d, ".env", "--example", os.path.join(d, ".env.example"), "--allow-empty")
    check("allow-empty suppress", code == 0)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("t_") and callable(fn):
            fn()
    total = _pass + _fail
    print(f"\n{_pass}/{total} passed")
    return 1 if _fail else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
