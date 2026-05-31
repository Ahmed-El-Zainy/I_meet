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
        hf_token = os.environ.get("HF_TOKEN")
        kwargs = {"token": hf_token} if hf_token else {}
        try:
            _diarize_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                **kwargs,
            )
        except TypeError:
            _diarize_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
    return _diarize_pipeline


def transcribe(audio_path: str) -> dict[str, Any]:
    """
    Run Whisper STT + pyannote diarization.
    Returns transcript dict matching the README output schema.
    """
    model = _get_whisper()

    # --- Diarization (optional) ---
    turns: list[tuple[float, float, str]] = []
    if os.environ.get("SKIP_DIARIZATION") != "1":
        try:
            diarizer = _get_diarizer()
            diarization = diarizer(audio_path)
            turns = [(seg.start, seg.end, spk) for seg, _, spk in diarization.itertracks(yield_label=True)]
        except Exception as exc:
            print(f"Diarization skipped: {exc}")

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
        lang = getattr(seg, "language", None) or info.language or "unknown"
        lang_seconds[lang] = lang_seconds.get(lang, 0) + duration

        logprob = seg.avg_logprob if seg.avg_logprob is not None else -1.0
        confidence = round(min(1.0, max(0.0, logprob + 1.0)), 2)

        entry: dict[str, Any] = {
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "speaker": _assign_speaker(seg.start, seg.end),
            "text": seg.text.strip(),
            "language": lang,
            "confidence": confidence,
        }
        if confidence < 0.75:
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
