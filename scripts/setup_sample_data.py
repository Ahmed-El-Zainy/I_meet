"""Copy provided recordings into data/sample_meetings/ with standardized names."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "sample_meetings"

MAPPING = [
    ("client1_meet_1.wav", "client_a_meeting_1.wav"),
    ("client1_meet2.wav", "client_a_meeting_2.wav"),
    ("client1_meet3.wav", "client_a_meeting_3.wav"),
    ("Client 2 Meeting 1.mp4", "client_b_meeting_1.mp4"),
    ("Client 2 Meeting 2.mp4", "client_b_meeting_2.mp4"),
    ("Client 2 Meeting 3.mp4", "client_b_meeting_3.mp4"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src_name, dst_name in MAPPING:
        src = DATA / src_name
        dst = OUT / dst_name
        if not src.exists():
            print(f"SKIP (missing): {src}")
            continue
        shutil.copy2(src, dst)
        print(f"OK: {dst_name}")
        copied += 1
    print(f"\nPrepared {copied}/{len(MAPPING)} files in {OUT}")


if __name__ == "__main__":
    main()
