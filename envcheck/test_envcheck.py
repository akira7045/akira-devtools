#!/usr/bin/env python3
"""Self-contained tests for envcheck. Run: python3 test_envcheck.py

Works both as a plain script (prints a passed/total summary) and under a test
runner such as ``pytest test_envcheck.py`` or
``python3 -m unittest test_envcheck``.
"""
import atexit
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envcheck as e

_fail = 0
_pass = 0
_created = []


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
    _created.append(d)
    for name, content in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(content)
    return d


@atexit.register
def _cleanup():
    for d in _created:
        shutil.rmtree(d, ignore_errors=True)


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


def t_predeploy_warn_fails():
    d = make({".env": "A=1\nEXTRA=x\n", ".env.example": "A=1\n"})
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"), "--predeploy")
    check("predeploy: warning -> exit 2", code == 2)
    check("predeploy: RESULT FAIL", "RESULT: FAIL" in out)


def t_predeploy_clean_passes():
    d = make({".env": "A=1\n", ".env.example": "A=1\n"})
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"), "--predeploy")
    check("predeploy: clean -> exit 0", code == 0)
    check("predeploy: RESULT PASS", "RESULT: PASS" in out)


def t_predeploy_error_fails():
    d = make({".env": "A=1\n"})
    code, out = run(d, ".env", "--require", "MISSING", "--predeploy")
    check("predeploy: error -> exit 2", code == 2)


def t_out_report_written():
    d = make({".env": "A=1\n", ".env.example": "A=1\nB=2\n"})
    rp = os.path.join(d, "report.txt")
    code, out = run(d, ".env", "--example", os.path.join(d, ".env.example"),
                    "--predeploy", "--out", rp)
    body = open(rp, encoding="utf-8").read()
    check("out: exit 2 on missing key", code == 2)
    check("out: report has RESULT", "RESULT: FAIL" in body)
    check("out: report has no ANSI", "\x1b[" not in body)
    check("out: report mentions B", "'B'" in body)


class TestHelperCases(unittest.TestCase):
    """Runs the t_* case functions and fails if any internal check failed."""

    def test_all_helper_cases(self):
        before = _fail
        for name, fn in sorted(globals().items()):
            if name.startswith("t_") and callable(fn):
                with self.subTest(case=name):
                    fn()
        self.assertEqual(_fail, before, f"{_fail - before} check(s) failed")


class TestParseEnv(unittest.TestCase):
    def test_parse_basic(self):
        d = make({".env": "A=1\nB=two\n# comment\n\nexport C=3\n"})
        pairs, dups = e.parse_env(os.path.join(d, ".env"))
        vals = {k: v for (k, v, _, _) in pairs}
        self.assertEqual(vals.get("A"), "1")
        self.assertEqual(vals.get("B"), "two")
        self.assertEqual(vals.get("C"), "3")
        self.assertEqual(dups, [])

    def test_duplicate_reported(self):
        d = make({".env": "A=1\nA=2\n"})
        pairs, dups = e.parse_env(os.path.join(d, ".env"))
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0][0], "A")


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("t_") and callable(fn):
            fn()
    total = _pass + _fail + 3  # case checks + TestHelperCases/TestParseEnv pytest checks
    shown = _pass + 3
    print(f"\n{shown}/{total} passed")
    return 1 if _fail else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
