"""Print final results for a processed meeting from the API."""
from __future__ import annotations

import json
import os
import sys

import requests

MEETING_ID = os.environ.get("DEMO_MEETING_ID", "client1-meeting-1")
API = os.environ.get("API_BASE_URL", "http://localhost:8000")
TOKEN = os.environ.get("CLIENT_A_TOKEN", "")


def main() -> int:
    if not TOKEN:
        print("CLIENT_A_TOKEN not set", file=sys.stderr)
        return 1
    headers = {"Authorization": f"Bearer {TOKEN}"}
    status = requests.get(f"{API}/meetings/{MEETING_ID}/status", headers=headers, timeout=10).json()
    summary = requests.get(f"{API}/meetings/{MEETING_ID}/summary", headers=headers, timeout=10)
    out = {"status": status}
    if summary.ok:
        out["summary"] = summary.json()
    else:
        out["summary_error"] = summary.text
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
