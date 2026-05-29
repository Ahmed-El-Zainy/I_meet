"""
Ingest all 6 sample meetings and poll until complete.
Run inside the API container:
    python -m scripts.ingest_samples
"""
import os
import time
import requests

API = os.environ.get("API_BASE_URL", "http://localhost:8000")

SAMPLES = [
    {"file": "data/sample_meetings/client_a_meeting_1.mp4", "client": "a", "title": "Client A — Meeting 1"},
    {"file": "data/sample_meetings/client_a_meeting_2.mp4", "client": "a", "title": "Client A — Meeting 2"},
    {"file": "data/sample_meetings/client_a_meeting_3.mp4", "client": "a", "title": "Client A — Meeting 3"},
    {"file": "data/sample_meetings/client_b_meeting_1.mp4", "client": "b", "title": "Client B — Meeting 1"},
    {"file": "data/sample_meetings/client_b_meeting_2.mp4", "client": "b", "title": "Client B — Meeting 2"},
    {"file": "data/sample_meetings/client_b_meeting_3.mp4", "client": "b", "title": "Client B — Meeting 3"},
]

TOKENS = {
    "a": os.environ.get("CLIENT_A_TOKEN", ""),
    "b": os.environ.get("CLIENT_B_TOKEN", ""),
}


def ingest(sample: dict) -> str:
    token = TOKENS[sample["client"]]
    client_id = f"client_{sample['client']}"
    with open(sample["file"], "rb") as f:
        resp = requests.post(
            f"{API}/meetings/ingest",
            headers={"Authorization": f"Bearer {token}"},
            files={"recording_file": (os.path.basename(sample["file"]), f, "video/mp4")},
            data={
                "client_id": client_id,
                "meeting_title": sample["title"],
                "participants": '["Speaker 1", "Speaker 2"]',
            },
            timeout=30,
        )
    resp.raise_for_status()
    meeting_id = resp.json()["meeting_id"]
    print(f"  Queued: {meeting_id} ({sample['title']})")
    return meeting_id


def poll(meeting_id: str, token: str, timeout: int = 1800):
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API}/meetings/{meeting_id}/status", headers=headers, timeout=10)
        resp.raise_for_status()
        status = resp.json()["status"]
        print(f"    {meeting_id}: {status}")
        if status == "complete":
            return True
        if status == "failed":
            print(f"    ERROR: {resp.json().get('error_message')}")
            return False
        time.sleep(15)
    print(f"    TIMEOUT: {meeting_id}")
    return False


def main():
    print("Ingesting sample meetings...")
    jobs = []
    for s in SAMPLES:
        if not os.path.exists(s["file"]):
            print(f"  SKIP (not found): {s['file']}")
            continue
        meeting_id = ingest(s)
        jobs.append((meeting_id, TOKENS[s["client"]]))

    print(f"\nPolling {len(jobs)} jobs...")
    for meeting_id, token in jobs:
        ok = poll(meeting_id, token)
        print(f"  {'✓' if ok else '✗'} {meeting_id}")

    print("\nDone.")


if __name__ == "__main__":
    main()
