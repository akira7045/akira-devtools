#!/usr/bin/env python3
"""Reference implementation: idempotent bulk-registration pipeline.

Demonstrates the architecture proposed for large product-registration jobs
(e.g. Yahoo! Shopping bulk listing): input normalization -> idempotent worker
with retry/backoff -> structured logging -> partial re-run of failures only.

Single file, zero third-party dependencies, Python 3.8+.

This is a runnable reference, not a vendor SDK. The "transport" is pluggable so
it can be wired to a real API in production.
"""
import argparse
import csv
import hashlib
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


log = logging.getLogger("registry")


@dataclass
class Product:
    sku: str
    title: str
    price: int
    stock: int


def load_products(path: str) -> List[Product]:
    """Load and normalize products from a CSV file.

    Expected header: sku,title,price,stock
    Raises ValueError on missing/invalid required fields so bad rows never
    reach the transport layer.
    """
    out: List[Product] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"sku", "title", "price", "stock"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        for i, row in enumerate(reader, start=2):
            sku = (row.get("sku") or "").strip()
            if not sku:
                raise ValueError(f"row {i}: empty sku")
            try:
                price = int(str(row["price"]).strip())
                stock = int(str(row["stock"]).strip())
            except (ValueError, TypeError):
                raise ValueError(f"row {i}: price/stock must be integers")
            if price < 0 or stock < 0:
                raise ValueError(f"row {i}: price/stock must be >= 0")
            out.append(Product(sku=sku, title=(row.get("title") or "").strip(),
                               price=price, stock=stock))
    return out


def idempotency_key(p: Product) -> str:
    """Stable key so retries never create duplicate records upstream."""
    raw = f"{p.sku}|{p.title}|{p.price}|{p.stock}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Result:
    ok: bool
    sku: str
    key: str
    attempts: int
    error: Optional[str] = None


@dataclass
class Worker:
    transport: Callable[[Product], None]
    max_attempts: int = 3
    base_delay: float = 0.0  # seconds; set >0 in real use for backoff
    seen: Dict[str, str] = field(default_factory=dict)  # key -> status

    def _sleep(self, attempt: int) -> None:
        if self.base_delay > 0:
            time.sleep(self.base_delay * (2 ** (attempt - 1)))

    def register_one(self, p: Product) -> Result:
        key = idempotency_key(p)
        # Idempotency: a previously successful key is not sent again.
        if self.seen.get(key) == "ok":
            log.info("skip duplicate sku=%s key=%s", p.sku, key[:12])
            return Result(True, p.sku, key, attempts=0)

        last_err = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                self.transport(p)
                self.seen[key] = "ok"
                log.info("registered sku=%s attempt=%d key=%s",
                         p.sku, attempt, key[:12])
                return Result(True, p.sku, key, attempt)
            except Exception as e:  # transport failures are retryable
                last_err = f"{type(e).__name__}: {e}"
                log.warning("failed sku=%s attempt=%d err=%s",
                            p.sku, attempt, last_err)
                self._sleep(attempt)

        self.seen[key] = "error"
        return Result(False, p.sku, key, self.max_attempts, last_err)

    def register_all(self, products: List[Product]) -> List[Result]:
        return [self.register_one(p) for p in products]


def write_report(results: List[Result], path: str) -> None:
    """Structured report for operations: failures can be re-run by SKU."""
    payload = {
        "total": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "items": [
            {"sku": r.sku, "key": r.key, "ok": r.ok,
             "attempts": r.attempts, "error": r.error}
            for r in results
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="input products CSV (sku,title,price,stock)")
    ap.add_argument("--report", default="registry-report.json")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    products = load_products(args.csv)

    # Placeholder transport: replace with a real API call in production.
    def transport(p: Product) -> None:
        log.debug("transport -> %s", p.sku)

    worker = Worker(transport=transport, max_attempts=args.max_attempts)
    results = worker.register_all(products)
    write_report(results, args.report)
    failed = sum(1 for r in results if not r.ok)
    log.info("done total=%d failed=%d report=%s",
             len(results), failed, args.report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
