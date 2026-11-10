#!/usr/bin/env python3
"""Tests for the akira_devtools package wiring (not the individual tools).

Verifies that every CLI the package advertises actually exists, is importable
from the installed layout, and behaves as documented for the dispatch entry
point. The individual tools have their own per-directory suites.

Run: python3 python/test_devtools_package.py
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

import akira_devtools  # noqa: E402
from akira_devtools import cli  # noqa: E402

TOOLS = ("secretscan", "apidiff", "jsonl2csv", "dupfind", "envcheck", "logsum")


class PackageShape(unittest.TestCase):
    def test_module_each_tool_importable(self):
        import importlib

        for name in TOOLS:
            mod = importlib.import_module(f"akira_devtools.{name}")
            self.assertTrue(callable(getattr(mod, "main", None)),
                            f"{name}.main must be callable")

    def test_cli_wrapper_each_tool(self):
        for name in TOOLS:
            fn = getattr(cli, f"{name}_main", None)
            self.assertTrue(callable(fn), f"cli.{name}_main must be callable")

    def test_tools_tuple_matches(self):
        self.assertEqual(tuple(sorted(akira_devtools._TOOLS)),
                         tuple(sorted(TOOLS)))

    def test_version_string(self):
        self.assertRegex(akira_devtools.__version__, r"^\d+\.\d+\.\d+$")


class Dispatcher(unittest.TestCase):
    def _run(self, argv):
        old = sys.argv
        sys.argv = ["akira-devtools"] + argv
        try:
            return akira_devtools.main()
        finally:
            sys.argv = old

    def test_help_lists_every_tool(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._run(["--help"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        for name in TOOLS:
            self.assertIn(name, out)

    def test_no_args_is_usage_error(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self._run([])
        self.assertEqual(rc, 2)

    def test_unknown_tool_is_usage_error(self):
        import io
        from contextlib import redirect_stderr

        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = self._run(["definitely-not-a-tool"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown tool", buf.getvalue())

    def test_dispatch_to_real_tool(self):
        # logsum with no input just summarises nothing; must exit cleanly.
        import io
        from contextlib import redirect_stdout, redirect_stderr

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self._run(["logsum", "--help"])
        self.assertEqual(cm.exception.code, 0)


class ConsoleScriptEquivalence(unittest.TestCase):
    """The package must not regress the standalone scripts it wraps."""

    def test_standalone_scripts_still_run(self):
        base = os.path.dirname(HERE)
        for name in TOOLS:
            script = os.path.join(base, name, f"{name}.py")
            self.assertTrue(os.path.isfile(script), script)
            proc = subprocess.run([sys.executable, script, "--help"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(proc.returncode, 0, f"{name}: {proc.stderr[:200]!r}")




if __name__ == "__main__":
    unittest.main(verbosity=2)
