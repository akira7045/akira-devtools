"""akira-devtools: zero-dependency developer tools.

Bundles six single-file CLI tools: secretscan, apidiff, jsonl2csv,
dupfind, envcheck, logsum.
"""
import sys

__version__ = "1.0.0"

_TOOLS = ("secretscan", "apidiff", "jsonl2csv", "dupfind", "envcheck", "logsum")


def _run(name):
    argv = sys.argv[1:]
    if name == "secretscan":
        from . import secretscan
        sys.argv = ["secretscan"] + argv
        return secretscan.main()
    from importlib import import_module
    mod = import_module(f".{name}", __name__)
    return mod.main(argv)


def main():
    """Entry point: `akira-devtools <tool> [args...]`."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: akira-devtools <tool> [args...]")
        print("tools: " + ", ".join(_TOOLS))
        return 0 if len(sys.argv) >= 2 else 2
    tool = sys.argv[1]
    if tool not in _TOOLS:
        print(f"unknown tool: {tool}", file=sys.stderr)
        print("tools: " + ", ".join(_TOOLS), file=sys.stderr)
        return 2
    return _run(tool)
