import os
from typing import Any

_pipeline = None
_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual"


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model=_MODEL,
            top_k=None,
            device=-1,  # CPU; change to 0 for GPU
        )
    return _pipeline


def _scores_to_dict(results: list) -> dict:
    return {r["label"].lower(): round(r["score"], 4) for r in results}


def _dominant(scores: dict) -> str:
    return max(scores, key=scores.get)


def analyze(transcript: dict[str, Any]) -> dict[str, Any]:
    clf = _get_pipeline()
    segments = transcript["segments"]
    duration = transcript.get("duration_seconds", 1) or 1

    # Per-segment scores
    texts = [s["text"][:512] for s in segments]  # model max 512 tokens
    all_scores = clf(texts, truncation=True, max_length=512)

    # Aggregate overall
    overall_acc = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    per_speaker: dict[str, list] = {}

    for seg, scores_raw in zip(segments, all_scores):
        scores = _scores_to_dict(scores_raw)
        for k in overall_acc:
            overall_acc[k] += scores.get(k, 0.0)
        spk = seg["speaker"]
        per_speaker.setdefault(spk, []).append((seg["start"], scores))

    n = len(segments) or 1
    overall = {k: round(v / n, 4) for k, v in overall_acc.items()}

    # Per-speaker with trajectory (10-min windows)
    window = 600  # seconds
    per_speaker_out = {}
    for spk, entries in per_speaker.items():
        spk_acc = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        for _, sc in entries:
            for k in spk_acc:
                spk_acc[k] += sc.get(k, 0.0)
        m = len(entries)
        spk_overall = {k: round(v / m, 4) for k, v in spk_acc.items()}

        # Build time windows
        max_t = max(t for t, _ in entries) if entries else 0
        windows = []
        w_start = 0
        while w_start <= max_t:
            w_end = w_start + window
            bucket = [sc for t, sc in entries if w_start <= t < w_end]
            if bucket:
                avg = {k: sum(sc.get(k, 0) for sc in bucket) / len(bucket) for k in spk_acc}
                dom = _dominant(avg)
                windows.append({
                    "time_window": f"{w_start // 60}-{w_end // 60}min",
                    "dominant": dom,
                    "score": round(avg[dom], 4),
                })
            w_start += window

        per_speaker_out[spk] = {"overall": spk_overall, "trajectory": windows}

    # Notable moments: segments where negative score > 0.6
    notable = []
    for seg, scores_raw in zip(segments, all_scores):
        scores = _scores_to_dict(scores_raw)
        if scores.get("negative", 0) > 0.6:
            t = int(seg["start"])
            notable.append({
                "timestamp": f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}",
                "speaker": seg["speaker"],
                "note": "sharp negative shift",
            })

    return {
        "overall": overall,
        "per_speaker": per_speaker_out,
        "topic_sentiment": [],   # populated by LLM if needed
        "notable_moments": notable,
    }
