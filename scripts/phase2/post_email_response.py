"""Post a simulated email reply to the webhook for testing."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import httpx


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    subject = args.subject
    if args.lead_id and f"[AORO-{args.lead_id}]" not in subject:
        subject = f"{subject} [AORO-{args.lead_id}]"

    return {
        "lead_id": args.lead_id,
        "email_id": args.email_id,
        "from_email": args.from_email,
        "to_email": args.to_email,
        "subject": subject,
        "content": args.content,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": "email",
        "metadata": {"lead_id": args.lead_id} if args.lead_id else {},
    }


def _load_latest_lead_id() -> str | None:
    outreach_path = Path("data/workflow_outreachs.json")
    if not outreach_path.exists():
        return None
    try:
        content = outreach_path.read_text()
        data = json.loads(content) if content.strip() else {}
    except Exception:
        return None

    if not isinstance(data, dict) or not data:
        return None

    latest_lead_id = None
    latest_ts = ""
    for lead_id, outreach_list in data.items():
        if not isinstance(outreach_list, list):
            continue
        for entry in outreach_list:
            sent_at = entry.get("sent_at", "")
            if sent_at > latest_ts:
                latest_ts = sent_at
                latest_lead_id = lead_id
    return latest_lead_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Post a simulated email reply to the webhook.")
    parser.add_argument("--base-url", default=os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--lead-id")
    parser.add_argument("--latest", action="store_true", help="Use most recent outreach lead_id")
    parser.add_argument("--from-email", required=True)
    parser.add_argument("--to-email", required=True)
    parser.add_argument("--subject", default="Re: Fire Safety Compliance Consultation")
    parser.add_argument("--content", required=True)
    parser.add_argument("--email-id", default=None)
    args = parser.parse_args()

    if args.latest:
        args.lead_id = _load_latest_lead_id()
    if not args.lead_id:
        raise SystemExit("lead_id is required (or pass --latest)")

    payload = _build_payload(args)
    url = f"{args.base_url.rstrip('/')}/webhooks/email-response"

    resp = httpx.post(url, json=payload, timeout=10.0)
    print(f"POST {url} -> {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)


if __name__ == "__main__":
    main()
