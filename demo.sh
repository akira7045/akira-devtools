#!/usr/bin/env bash
# demo.sh - Try all AKIRA Dev Tools in one command, with zero setup.
# Creates a throwaway temp dir, feeds each tool sample input, prints the result.
# Nothing in your project is touched. Safe to run anywhere.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
B="\033[1m"; N="\033[0m"

hr(){ printf '%s\n' "------------------------------------------------------------"; }

echo -e "${B}AKIRA Dev Tools - one-command demo${N}"
echo "temp workspace: $TMP (removed on exit)"
hr

echo -e "${B}[1/6] secretscan${N} - scan a file for hardcoded secrets (read-only)"
cat > "$TMP/leak.py" <<'EOF'
API_KEY = "sk_live_1234567890abcdef"
password = "hunter2"
db = "postgres://user:pass@localhost/db"
EOF
python3 "$HERE/secretscan/secretscan.py" "$TMP/leak.py" 2>/dev/null || true
hr

echo -e "${B}[2/6] apidiff${N} - compare two JSON API responses for drift"
cat > "$TMP/old.json" <<'EOF'
{"id":1,"name":"alice","role":"admin"}
EOF
cat > "$TMP/new.json" <<'EOF'
{"id":1,"name":"alice","email":"a@x.io"}
EOF
python3 "$HERE/apidiff/apidiff.py" diff "$TMP/old.json" "$TMP/new.json" 2>/dev/null || true
hr

echo -e "${B}[3/6] jsonl2csv${N} - convert JSONL to CSV with no jq expressions"
cat > "$TMP/data.jsonl" <<'EOF'
{"id":1,"user":"alice","score":10}
{"id":2,"user":"bob","score":20}
EOF
python3 "$HERE/jsonl2csv/jsonl2csv.py" "$TMP/data.jsonl" 2>/dev/null || true
hr

echo -e "${B}[4/6] dupfind${N} - find duplicate files (read-only, NEVER deletes)"
echo "hello" > "$TMP/a.txt"; cp "$TMP/a.txt" "$TMP/b.txt"; echo "other" > "$TMP/c.txt"
python3 "$HERE/dupfind/dupfind.py" "$TMP" 2>/dev/null || true
hr

echo -e "${B}[5/6] envcheck${N} - lint a .env against a template (never prints secrets)"
printf 'A=1\nB=\n' > "$TMP/.env"
printf 'A=\nB=\nC=\n' > "$TMP/.env.example"
python3 "$HERE/envcheck/envcheck.py" "$TMP/.env" --example "$TMP/.env.example" 2>/dev/null || true
hr

echo -e "${B}[6/6] logsum${N} - summarize logs into counts (read-only)"
cat > "$TMP/access.log" <<'EOF'
1.2.3.4 - - [09/Nov/2026:12:00:00 +0000] "GET /a" 200 12
1.2.3.4 - - [09/Nov/2026:12:00:01 +0000] "GET /a" 200 0
5.6.7.8 - - [09/Nov/2026:12:00:02 +0000] "POST /b" 500 0
EOF
python3 "$HERE/logsum/logsum.py" --format access --by status "$TMP/access.log" 2>/dev/null || true
hr
echo -e "${B}Done.${N} Each tool is a single stdlib-only Python file. Copy one file and go."
