# dupfind

Zero-dependency duplicate file finder. Groups files by SHA-256 content hash and
tells you how much space you can reclaim — without ever deleting anything.

## Why

`fdupes`, `rdfind`, etc. are great but often need installing. `dupfind` is a
single pure-Python-3 stdlib file. Runs anywhere Python 3.7+ runs. Read-only by
design: it never modifies or deletes your files. If you want a removal plan, it
generates a review-ready shell script instead of acting on its own.

## Features

- Content-based (SHA-256), not name/size based
- Fast: groups by size first, only hashes files that share a size
- `--json` for scripting and reporting
- `--dedupe-script` emits a `rm` script you can inspect before running
- Handles filenames with spaces and quotes safely
- Exit codes for CI: `0` clean, `1` duplicates found, `2` bad path

## Usage

```bash
python3 dupfind.py ~/Downloads              # human-readable report
python3 dupfind.py --json ~/Downloads       # machine-readable
python3 dupfind.py --min-size 1048576 .     # ignore files under 1 MiB
python3 dupfind.py --empty .                # also group zero-byte files
python3 dupfind.py --dedupe-script . > rm.sh   # review, then run
```

Sample output:

```
e3b0c44298fc1c14  18.0MiB  x3
    /home/me/backup/a.iso
    /home/me/downloads/a.iso
    /home/me/tmp/a-copy.iso

1 duplicate group(s), 36.0MiB reclaimable.
```

## Safety

`dupfind` is strictly read-only. `--dedupe-script` only *prints* commands; you
decide whether to run them. The script keeps the first path in each group and
guards the `rm` calls with `--`.

## Install

No install needed. Copy `dupfind.py` anywhere and run it with Python 3.7+.

## Tests

```bash
python3 test_dupfind.py    # 18 cases, no external dependencies
```

## License

MIT. See LICENSE.
