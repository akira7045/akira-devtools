#!/usr/bin/env python3
"""Self-contained tests for secretscan. Run: python3 test_secretscan.py"""
import secretscan as s

CASES = [
    ('password = "supersecretvalue123"', True),
    ('PASSWORD="hunter2hunter2"', True),
    ('db_password = "Tr0ub4dor&3xyz"', True),
    ('access_token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"', True),
    ('key=AKIA1234567890ABCDEF', True),
    ('password = "aaaaaaaaaaaa"', False),
    ('token: ""', False),
    ('svc_api_key = "abcd"', False),
    ('password = os.environ["PW"]', False),
    ('token_url = "https://api.example.com"', False),
    ('self.password = password', False),
    ('AKIAIOSFODNN7EXAMPLE', False),
    ('x = 1', False),
]


def main():
    failed = 0
    for line, expect in CASES:
        fired = len(s.scan_line(line, 2.0)) > 0
        if fired != expect:
            failed += 1
            print(f"FAIL: {line!r} expected={expect} got={fired}")
        else:
            print(f"ok: {line!r} -> {fired}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
