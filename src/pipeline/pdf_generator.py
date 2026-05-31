import unicodedata
from typing import Any


def _normalize_arabic(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _sentiment_svg(overall: dict) -> str:
    pos = overall.get("positive", 0) * 100
    neu = overall.get("neutral", 0) * 100
    neg = overall.get("negative", 0) * 100
    return f"""<svg width="300" height="30" xmlns="http://www.w3.org/2000/svg">
  <rect x="0"   y="5" width="{pos:.1f}%" height="20" fill="#4caf50"/>
  <rect x="{pos:.1f}%" y="5" width="{neu:.1f}%" height="20" fill="#9e9e9e"/>
  <rect x="{pos + neu:.1f}%" y="5" width="{neg:.1f}%" height="20" fill="#f44336"/>
  <text x="2" y="18" font-size="10" fill="white">+{pos:.0f}%</text>
  <text x="{pos + neu / 2:.0f}" y="18" font-size="10" fill="white">{neu:.0f}%</text>
  <text x="{pos + neu + 2:.0f}" y="18" font-size="10" fill="white">-{neg:.0f}%</text>
</svg>"""


def _html(meeting_title: str, meeting_date: str, participants: list[str],
          client_id: str, summary: dict, sentiment: dict,
          segments: list[dict]) -> str:

    def row(cells):
        return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    action_rows = "".join(
        row([a.get("item", ""), a.get("assignee") or "—", a.get("deadline") or "—"])
        for a in summary.get("action_items", [])
    )
    decision_rows = "".join(
        row([d.get("decision", ""), d.get("made_by", ""), d.get("timestamp", "")])
        for d in summary.get("decisions_made", [])
    )
    transcript_rows = "".join(
        f'<tr><td>{s["start"]:.1f}s</td><td>{s["speaker"]}</td>'
        f'<td dir="auto">{_normalize_arabic(s["text"])}</td></tr>'
        for s in segments
    )
    key_points = "".join(f"<li>{_normalize_arabic(p)}</li>" for p in summary.get("key_discussion_points", []))
    open_qs = "".join(f"<li>{_normalize_arabic(q)}</li>" for q in summary.get("open_questions", []))
    participants_str = ", ".join(participants)
    overall = sentiment.get("overall", {})

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  @font-face {{
    font-family: 'NotoNaskh';
    src: url('/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf');
  }}
  body {{ font-family: 'NotoNaskh', sans-serif; margin: 40px; color: #222; }}
  h1, h2 {{ color: #1a237e; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; }}
  th {{ background: #e8eaf6; }}
  .rtl {{ direction: rtl; unicode-bidi: embed; text-align: right; }}
  .cover {{ text-align: center; padding: 60px 0; border-bottom: 2px solid #1a237e; margin-bottom: 40px; }}
</style>
</head>
<body>

<div class="cover">
  <h1 dir="auto">{_normalize_arabic(meeting_title)}</h1>
  <p><strong>Date:</strong> {meeting_date}</p>
  <p><strong>Client:</strong> {client_id}</p>
  <p><strong>Participants:</strong> {participants_str}</p>
</div>

<h2>Executive Summary</h2>
<p dir="auto" class="rtl">{_normalize_arabic(summary.get("executive_summary", ""))}</p>

<h2>Key Discussion Points</h2>
<ul>{key_points}</ul>

<h2>Decisions Made</h2>
<table><tr><th>Decision</th><th>Made By</th><th>Timestamp</th></tr>{decision_rows}</table>

<h2>Action Items</h2>
<table><tr><th>Item</th><th>Assignee</th><th>Deadline</th></tr>{action_rows}</table>

<h2>Open Questions</h2>
<ul>{open_qs}</ul>

<h2>Sentiment Analysis</h2>
{_sentiment_svg(overall)}
<p>Positive: {overall.get("positive", 0):.0%} &nbsp;
   Neutral: {overall.get("neutral", 0):.0%} &nbsp;
   Negative: {overall.get("negative", 0):.0%}</p>

<h2>Full Transcript</h2>
<table>
  <tr><th>Time</th><th>Speaker</th><th>Text</th></tr>
  {transcript_rows}
</table>

</body>
</html>"""


def generate_pdf(meeting_title: str, meeting_date: str, participants: list[str],
                 client_id: str, summary: dict, sentiment: dict,
                 segments: list[dict]) -> bytes:
    """Render HTML → PDF bytes using WeasyPrint."""
    from weasyprint import HTML
    html = _html(meeting_title, meeting_date, participants, client_id, summary, sentiment, segments)
    return HTML(string=html).write_pdf()
