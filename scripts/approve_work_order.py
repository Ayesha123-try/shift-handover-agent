"""Human approval step for draft work orders.

The agent can only create drafts in drafts/work_orders/. A person reviews them
here. Approved drafts move to drafts/work_orders/approved/, rejected ones to
drafts/work_orders/rejected/, with the reviewer's name and time added.

    python scripts/approve_work_order.py            # list pending drafts
    python scripts/approve_work_order.py <file> --approve --by "A. Siddiqui"
    python scripts/approve_work_order.py <file> --reject  --by "A. Siddiqui" --reason "Already planned"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DRAFTS = Path(__file__).resolve().parents[1] / "drafts" / "work_orders"


def pending() -> list[Path]:
    return sorted(DRAFTS.glob("DRAFT-*.json"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--approve", action="store_true")
    g.add_argument("--reject", action="store_true")
    ap.add_argument("--by", help="Reviewer name")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    if not args.file:
        drafts = pending()
        if not drafts:
            print("No pending drafts.")
        for p in drafts:
            d = json.loads(p.read_text(encoding="utf-8"))
            print(f"{p.name}\n  [{d['priority']}] {d['line']} {d['machine']} {d['failure_mode']}: {d['title']}\n"
                  f"  why: {d['justification']}\n  sop: {d.get('sop_reference')}\n")
        return 0

    path = Path(args.file)
    if not path.is_absolute():
        path = DRAFTS / path.name
    if not (args.approve or args.reject) or not args.by:
        print("Choose --approve or --reject, and give --by <your name>.", file=sys.stderr)
        return 2
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update({
        "status": "APPROVED" if args.approve else "REJECTED",
        "reviewed_by": args.by,
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "review_reason": args.reason,
    })
    dest = DRAFTS / ("approved" if args.approve else "rejected")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / path.name.replace("DRAFT-", "")).write_text(json.dumps(record, indent=2), encoding="utf-8")
    path.unlink()
    print(f"{record['status']}: moved to {dest.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
