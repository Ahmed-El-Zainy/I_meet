import os
from typing import Any

# faster-whisper + pyannote loaded lazily to avoid import cost at startup
_whisper_model = None
_diarize_pipeline = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(
            os.environ.get("WHISPER_MODEL", "large-v3"),
            device=os.environ.get("WHISPER_DEVICE", "cpu"),
            compute_type="float16" if os.environ.get("WHISPER_DEVICE", "cpu") != "cpu" else "int8",
        )
    return _whisper_model


def _get_diarizer():
    global _diarize_pipeline
    if _diarize_pipeline is None:
        from pyannote.audio import Pipeline
        _diarize_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.environ.get("HF_TOKEN"),
        )
    return _diarize_pipeline


def transcribe(audio_path: str) -> dict[str, Any]:
    """
    Run Whisper STT + pyannote diarization.
    Returns transcript dict matching the README output schema.
    """
    model = _get_whisper()
    diarizer = _get_diarizer()

    # --- Diarization ---
    import torch
    diarization = diarizer(audio_path)
    # Build speaker turn map: list of (start, end, speaker)
    turns = [(seg.start, seg.end, spk) for seg, _, spk in diarization.itertracks(yield_label=True)]

    # --- Transcription (no forced language — multilingual) ---
    segments_raw, info = model.transcribe(audio_path, beam_size=5, word_timestamps=False)

    def _assign_speaker(start: float, end: float) -> str:
        mid = (start + end) / 2
        for t_start, t_end, spk in turns:
            if t_start <= mid <= t_end:
                return spk
        return "SPEAKER_UNKNOWN"

    segments = []
    lang_seconds: dict[str, float] = {}

    for seg in segments_raw:
        duration = seg.end - seg.start
        lang = seg.language or info.language
        lang_seconds[lang] = lang_seconds.get(lang, 0) + duration

        entry: dict[str, Any] = {
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "speaker": _assign_speaker(seg.start, seg.end),
            "text": seg.text.strip(),
            "language": lang,
            "confidence": round(seg.avg_logprob and min(1.0, (seg.avg_logprob + 1.0)), 2),
        }
        if entry["confidence"] < 0.75:
            entry["low_confidence"] = True
        segments.append(entry)

    total = sum(lang_seconds.values()) or 1
    language_mix = {lang: round(secs / total, 2) for lang, secs in lang_seconds.items()}
    duration = segments[-1]["end"] if segments else 0

    return {
        "segments": segments,
        "language_mix": language_mix,
        "duration_seconds": int(duration),
    }
