import os
import json
from typing import Any

_SYSTEM_PROMPT = """You are a meeting analyst. Given a meeting transcript, return ONLY a valid JSON object
with this exact schema (no markdown, no extra text):
{
  "executive_summary": "<3-5 sentences>",
  "key_discussion_points": ["..."],
  "decisions_made": [{"decision": "...", "made_by": "SPEAKER_XX", "timestamp": "HH:MM:SS"}],
  "action_items": [{"item": "...", "assignee": "<name or null>", "deadline": "<date or null>"}],
  "open_questions": ["..."]
}
Respond in the same language(s) as the meeting. If a segment was marked low_confidence, note it as [low confidence transcript]."""


def _format_transcript(segments: list[dict]) -> str:
    lines = []
    for s in segments:
        flag = " [low confidence transcript]" if s.get("low_confidence") else ""
        lines.append(f"[{s['speaker']} {s['start']:.0f}s] {s['text']}{flag}")
    return "\n".join(lines)


def summarize(transcript: dict[str, Any]) -> dict[str, Any]:
    provider = os.environ.get("LLM_PROVIDER", "openai")
    model = os.environ.get("LLM_MODEL", "gpt-4o")
    text = _format_transcript(transcript["segments"])

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        return json.loads(resp.choices[0].message.content)

    elif provider == "ollama":
        import requests
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=300,
        )
        resp.raise_for_status()
        return json.loads(resp.json()["message"]["content"])

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
