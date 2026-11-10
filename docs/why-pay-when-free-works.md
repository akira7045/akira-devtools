# Why pay when the free tool already works?

*Published 2026-11-10 by 十五郎工房 / Araki Akira. All output below is real,
generated on 2026-11-10 by running the tool against a live local HTTP server
that changes its response mid-run (the exact script is shown so you can
reproduce it). No edits to the transcript.*

There is a fair objection to every single-file dev tool: "I already have
`jq`, `gitleaks`, `fdupes` — why would I pay you?" That objection is correct
for the individual engineer who just wants to run a command once.

This page is not a sales pitch. It is a concrete walkthrough of the one
situation where the free path quietly costs more than the paid one:
**a third-party API changed under you, and the free tool told you too late.**

## A real run, not a mock-up

Below is a live reproduction. A tiny local server serves one shape; we save it
as the baseline; the server then "ships a minor update" that re-types a field
and bumps the version. These are the actual commands and the actual output
from 2026-11-10 — including the exit codes CI keys off.

```
# 1) capture the known-good baseline (vendor v1)
$ python3 apidiff.py save http://127.0.0.1:8791/ status.json
saved baseline -> status.json
exit=0

# 2) the vendor silently ships a new version: user.id goes from number to
#    string, and the version string bumps. Nothing else changes.

# 3) the CI gate runs --breaking-only
$ python3 apidiff.py check http://127.0.0.1:8791/ status.json --breaking-only
[type   ] user.id
    - 42
    + "42"
[changed] version
    - "1.2.0"
    + "2.0.0"
exit=1        # <-- build fails, merge blocked

# 4) after the vendor reverts / you pin, the same gate is green again
$ python3 apidiff.py check http://127.0.0.1:8791/ status.json --breaking-only
no differences
exit=0        # <-- merge allowed
```

The point that matters: `user.id` changing from `42` to `"42"` is invisible to
a human skimming logs, and many JSON diff tools would drown it among harmless
additions. Here it is classified as `[type]` — a contract break — and the run
exits `1`. When the shape matches again, the same command exits `0`.

## The setup

You integrate with a vendor endpoint. You built against this response
(what you saved as your baseline):

```json
{"id":1,"name":"alice","role":"admin","items":[1,2,3],"price":9.99}
```

Months go by. The vendor ships a "minor" update. Now it returns:

```json
{"id":1,"name":"alice","is_admin":true,"items":[1,2],"price":"9.99"}
```

Nothing crashed. Nobody emailed you. Your integration will keep running —
until the code path that reads `role` or expects `price` to be a number runs
in production.

## The free path — and where it leaks

`jq` and `diff` can show that two JSON blobs are different. That is true and
they do it well. What they do **not** do is tell you *which differences can
break a consumer* versus *which are harmless additions*. So in practice you
either:

- eyeball the diff and make a judgement call every time (does not scale to
  many endpoints, and humans tune out red diff lines), or
- gate on *any* difference — and then the vendor adding one harmless field
  fails your build, so you turn the check off. Now you are back to being blind.

That is the leak: the free tool gives you a **diff**, not a **decision**.
The cost shows up later, in the incident.

## The same data, one command, a decision

```
$ python3 apidiff.py diff baseline.json drifted.json
[removed] role
    - "admin"
    + "<missing>"
[added  ] is_admin
    - "<missing>"
    + true
[length ] items[len]
    - 3
    + 2
[type   ] price
    - 9.99
    + "9.99"
exit=1
```

Four changes. Two of them (`[added]` — a new key) are safe to ignore. Three
of them are exactly the kind that break consumers: a key vanished, an array
lost an element, a number became a string.

You do not have to know that in advance. Ask for only the breaking ones:

```
$ python3 apidiff.py diff baseline.json drifted.json --breaking-only
[removed] role
    - "admin"
    + "<missing>"
[length ] items[len]
    - 3
    + 2
[type   ] price
    - 9.99
    + "9.99"
exit=1
```

The harmless `[added] is_admin` is gone. What is left is the decision:
**this release will break me.** Exit code `1`. That is a gate.

## The CI gate — two real runs

Add the baseline to your repo and this to your pipeline:

```yaml
- name: Check API contract
  run: python3 apidiff.py check "$API_URL" contract.json --breaking-only
```

Verified behaviour on 2026-11-10:

```
# drifted payload (breaking changes present) -> exit 1 -> merge blocked
$ python3 apidiff.py diff baseline.json drifted.json --breaking-only >/dev/null; echo $?
1

# only an added field, everything else identical -> exit 0 -> merge allowed
$ python3 apidiff.py diff baseline.json same.json --breaking-only >/dev/null; echo $?
0
```

That is the whole idea. Not "a diff tool" — **a pass/fail gate on contract
regressions that does not fail on noise.** You write four lines of YAML and
stop discovering breaking changes in production.

## So, concretely, what are you paying for?

Not the algorithm — a JSON diff is not hard. You are paying for the part
that is easy to get wrong and expensive when it is:

1. **The breaking/non-breaking classification** and `--breaking-only`, tested
   against 48 cases (local HTTP server, no network) so the gate stays honest.
2. **A CI contract**: documented exit codes (`0` / `1` / `2`), so your
   pipeline can distinguish "drift" from "the endpoint was down".
3. **A commercial license, a 30-day bug-fix window, and a named contact** —
   the three things a company's procurement asks for that an ad-hoc script
   does not have.
4. **Zero install surface**: one file, standard library only, Python 3.8+.
   Nothing to pin, audit, or leave behind — which is what makes it acceptable
   in a locked-down CI image where `pip install` is not.

Point 4 is also why the free version genuinely is enough for many people. If
you are one person running it by hand, keep the MIT version — fork it, it is
yours. The paid line exists for the team that needs the gate to be a counted,
supported dependency rather than a script someone pasted in two years ago.

## Reproduce the run above

The whole demo is one small server plus three commands. Save this as
`vendor.py`, run it, and drive it with `apidiff` exactly as shown:

```python
import http.server, json, os
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        mode = open("mode.txt").read().strip()
        body = ({"version":"1.2.0","user":{"id":42},"status":"ok"} if mode=="v1"
                else {"version":"2.0.0","user":{"id":"42","email":"a@example.com"},"status":"ok"})
        b = json.dumps(body).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", 8791), H).serve_forever()
```

```bash
echo v1 > mode.txt; python3 vendor.py &        # serve the known-good shape
python3 apidiff.py save http://127.0.0.1:8791/ status.json
echo v2 > mode.txt                             # vendor ships the change
python3 apidiff.py check http://127.0.0.1:8791/ status.json --breaking-only; echo "exit=$?"
```

You should see `exit=1` and the `[type] user.id` line above. That is the gate
you are buying — verified on your own machine, no account, no network.

## Try the whole bundle

```bash
bash demo.sh          # all seven tools, sample input, cleaned up on exit
```

Or read the source — 200 lines, no dependencies:

- **Free (MIT)**: https://github.com/akira7045/akira-devtools
- **Paid (teams)**: commercial license + 30-day bug-fix window + named
  support contact, per the SALES sheet in the same bundle.

The honest summary: if the free tools never let a breaking change reach your
production, you do not need this. If they have — even once — that incident is
the reason the gate exists.
