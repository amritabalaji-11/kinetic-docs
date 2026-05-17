#!/usr/bin/env python3
"""
Kinetic AI — User Format Test
Runs Sonnet on V1, V3, V5 with two output schemas:
  Variant K — Option A: Priority Issues (ranked, causal chain)
  Variant L — Option B: Analysis Layer + 4 Parameters

Generates: user_test/format_comparison.html
           user_test/raw_outputs.json

Usage:
  export ANTHROPIC_API_KEY=your_key
  python user_test.py
"""

import os, re, json, time, base64, cv2
from pathlib import Path
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL             = "claude-sonnet-4-6"
FRAMES_PER_VIDEO  = 8
VIDEO_IDS         = ["V1", "V3", "V5"]

VIDEOS_DIR = Path("videos")
JSON_DIR   = Path("json")
OUT_DIR    = Path("user_test")
OUT_DIR.mkdir(exist_ok=True)

VIDEO_FILES = {
    "V1": VIDEOS_DIR / "v1_depth_fault.mp4",
    "V3": VIDEOS_DIR / "v3_knee_fault.mp4",
    "V5": VIDEOS_DIR / "v5_torso_fault.mp4",
}
JSON_FILES = {
    "V1": JSON_DIR / "v1.json",
    "V3": JSON_DIR / "v3.json",
    "V5": JSON_DIR / "v5.json",
}
FAULT_LABELS = {
    "V1": "Insufficient depth",
    "V3": "Knee valgus (inward collapse)",
    "V5": "Excessive forward lean",
}

SYSTEM_PROMPT = (
    "You are a biomechanics analyst evaluating squat form for a fitness coaching "
    "application. Analyze the provided data and return structured feedback. "
    "Respond ONLY in valid JSON. No prose or markdown outside the JSON object."
)

SHARED_CONTEXT = """
## Angle Convention — When the Inversion Applies
MediaPipe uses interior angles for joint flexion measurements only.
The inversion rule (MediaPipe = 180° − flexion) applies to:
  knee_angle  — lower value = deeper squat (more flexion)
  hip_angle   — lower value = more hip flexion
All other angles (back_angle, valgus, foot_angle) compare directly.
When comparing visual to JSON for knee/hip: convert first (±10° tolerance).

## Movement Context
This is a GOBLET SQUAT. The athlete holds a weight at chest height.
- Torso should be upright; slight forward lean acceptable but no slouching
- Hip crease at or below knee defines sufficient depth
- Excessive lean signals a mobility or technique issue

## Analysis Requirements
For every issue identified, you MUST state:
  1. Rep count    — how many valid reps show this issue (e.g. "4 of 5 reps")
  2. Which reps   — specific rep numbers
  3. Trend        — direction and magnitude using trend fields in JSON
                    (e.g. "worsening +0.9°/rep" or "stable across set")
  4. Severity     — actual values, not just labels
                    (e.g. "back_angle 46.4°" not "excessive lean")

Bilateral check (mandatory):
  Compare foot_turnout_left vs foot_turnout_right.
  If difference > 10°, flag explicitly with likely cause.

Causal chain (mandatory when multiple issues co-exist):
  Start from the most impactful issue. Identify which is root cause,
  which are downstream. State the chain explicitly and connect them —
  do NOT list co-occurring faults as separate unconnected issues.

Walk-in/walk-out: if first or last rep duration is ≥ 3× median,
  include in rep_count but exclude entirely from all feedback.

Valgus rule: ignore valgus_flag boolean. Use knee_valgus_distance per rep.
  Flag knee_valgus only if ≥ 50% of valid reps have distance < 0.22.
"""


# ── FRAME EXTRACTION ─────────────────────────────────────────────────────────

def extract_frames(video_path: Path, n: int = FRAMES_PER_VIDEO) -> list[str]:
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = [int(i * total / n) for i in range(n)]
    frames_b64 = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames_b64.append(base64.b64encode(buf).decode("utf-8"))
    cap.release()
    return frames_b64


def build_composite(frames_b64: list[str], cols: int = 4) -> str:
    import math, numpy as np
    frames = []
    for b64 in frames_b64:
        buf = base64.b64decode(b64)
        arr = cv2.imdecode(np.frombuffer(buf, dtype=np.uint8), cv2.IMREAD_COLOR)
        if arr is not None:
            frames.append(arr)
    rows = math.ceil(len(frames) / cols)
    h, w = frames[0].shape[:2]
    tw, th = min(w, 320), min(h, 240)
    grid_rows = []
    for r in range(rows):
        row_frames = frames[r * cols:(r + 1) * cols]
        while len(row_frames) < cols:
            row_frames.append(np.zeros((th, tw, 3), dtype=np.uint8))
        grid_rows.append(np.hstack([cv2.resize(f, (tw, th)) for f in row_frames]))
    grid = np.vstack(grid_rows)
    _, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode("utf-8")


# ── PROMPTS ───────────────────────────────────────────────────────────────────

OPTION_A_SCHEMA = """
## Output — FORMAT A: Priority Issues
Respond with this exact JSON. Rank issues by impact (most impactful first).
Include 1–3 issues maximum. Only include an issue if it is genuinely present.

{
  "verdict": "<2–3 sentences. Action-oriented, second person. Start with the most impactful fix. If fixing one issue will affect another, say so explicitly.>",
  "issues": [
    {
      "rank": 1,
      "label": "<short name of the issue>",
      "type": "<root_cause | downstream | contributing_factor>",
      "reps_affected": "<X of Y valid reps>",
      "which_reps": "<rep numbers, e.g. reps 2, 3, 4>",
      "severity": "<actual measured value, e.g. back_angle 46.4° at bottom>",
      "trend": "<stable | improving | worsening +X per rep>",
      "caused_by": "<name of root cause if this is downstream, else null>",
      "causes": ["<downstream effects this issue creates, if any>"],
      "recommendation": "<one specific actionable cue with a drill or count if relevant>"
    }
  ],
  "doing_well": [
    "<1–2 specific things the user is doing well — state the actual metric, not generic praise>"
  ]
}
"""

OPTION_B_SCHEMA = """
## Output — FORMAT B: Analysis + Parameters
Respond with this exact JSON.

{
  "verdict": "<2–3 sentences. Action-oriented, second person. Start with the most impactful fix. If fixing one issue will affect another, say so explicitly.>",
  "analysis": {
    "primary_issue": "<name of the most impactful fault>",
    "causal_chain": "<root cause → effect → effect, e.g. ankle restriction → forward lean → depth deficit>",
    "chain_explained": "<1–2 sentences explaining why this chain exists biomechanically>",
    "worsening_trends": ["<metric name + direction + magnitude, e.g. back_angle worsening +0.9°/rep>"],
    "asymmetry_flags": ["<any left/right asymmetry > 10°, or empty array>"],
    "rep_summary": {
      "total_reps": "<integer>",
      "valid_reps": "<integer — excluding walk-in/out>",
      "walk_in_out_excluded": ["<which reps excluded and why>"],
      "fault_reps": {
        "<fault_name>": "<X of Y valid reps, which ones>"
      }
    }
  },
  "feedback": {
    "posture": {
      "doing_well": "<1–2 sentences — specific metric if positive>",
      "critical_observations": "<1–2 sentences with rep count and trend, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "stability": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences with rep count and trend, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "movement_quality": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences with rep count and trend, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "range_of_motion": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences with rep count and trend, or null>",
      "recommendation": "<one specific actionable cue>"
    }
  }
}
"""


def build_prompt(mediapipe_json: dict, schema: str, n_frames: int) -> str:
    visual_context = (
        f"Attached: a composite grid of {n_frames} frames sampled from the original squat video."
    )
    return f"""{visual_context}

{SHARED_CONTEXT}

## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}

{schema}"""


def extract_json(raw: str) -> dict:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if fence:
        raw = fence.group(1)
    return json.loads(raw)


# ── RUNNER ────────────────────────────────────────────────────────────────────

def run(mediapipe_json: dict, video_path: Path, schema: str, schema_name: str) -> tuple[dict, float]:
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    frames  = extract_frames(video_path)
    composite = build_composite(frames)
    prompt  = build_prompt(mediapipe_json, schema, len(frames))

    start   = time.time()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": composite,
            }},
            {"type": "text", "text": prompt},
        ]}],
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.content[0].text), latency_ms


# ── HTML GENERATOR ────────────────────────────────────────────────────────────

def format_option_a(data: dict) -> str:
    lines = []
    verdict = data.get("verdict", "")
    lines.append(f'<div class="verdict"><strong>Summary:</strong> {verdict}</div>')

    for issue in data.get("issues", []):
        tag = issue.get("type", "").replace("_", " ").title()
        trend = issue.get("trend", "")
        trend_cls = "trend-bad" if "worsening" in trend else ("trend-ok" if "stable" in trend else "trend-good")
        chain = ""
        if issue.get("caused_by"):
            chain = f'<div class="chain">↳ Caused by: <strong>{issue["caused_by"]}</strong></div>'
        if issue.get("causes"):
            chain += f'<div class="chain">↳ Also causes: <strong>{", ".join(issue["causes"])}</strong></div>'
        lines.append(f"""
        <div class="issue">
          <div class="issue-header">
            <span class="rank">#{issue.get("rank","")}</span>
            <span class="issue-label">{issue.get("label","")}</span>
            <span class="issue-type">{tag}</span>
          </div>
          {chain}
          <div class="issue-meta">
            <span>📊 {issue.get("reps_affected","")} &nbsp;|&nbsp; reps {issue.get("which_reps","")}</span>
            <span class="{trend_cls}">📈 {trend}</span>
          </div>
          <div class="severity">Measured: {issue.get("severity","")}</div>
          <div class="rec">→ {issue.get("recommendation","")}</div>
        </div>""")

    if data.get("doing_well"):
        lines.append('<div class="doing-well"><strong>✅ What\'s working:</strong><ul>')
        for item in data["doing_well"]:
            lines.append(f"<li>{item}</li>")
        lines.append("</ul></div>")

    return "\n".join(lines)


def format_option_b(data: dict) -> str:
    lines = []
    verdict = data.get("verdict", "")
    lines.append(f'<div class="verdict"><strong>Summary:</strong> {verdict}</div>')

    analysis = data.get("analysis", {})
    if analysis:
        chain = analysis.get("causal_chain", "")
        explained = analysis.get("chain_explained", "")
        trends = analysis.get("worsening_trends", [])
        asym = analysis.get("asymmetry_flags", [])
        rs = analysis.get("rep_summary", {})

        lines.append('<div class="analysis-block">')
        if chain:
            lines.append(f'<div class="causal-chain">🔗 <strong>Root cause chain:</strong> {chain}</div>')
        if explained:
            lines.append(f'<div class="chain-explain">{explained}</div>')
        if trends:
            lines.append(f'<div class="trends">📈 <strong>Worsening trends:</strong> {" &nbsp;|&nbsp; ".join(trends)}</div>')
        if asym:
            lines.append(f'<div class="asym">⚠️ <strong>Asymmetry:</strong> {" &nbsp;|&nbsp; ".join(asym)}</div>')
        if rs:
            fault_reps = " &nbsp;|&nbsp; ".join(f"{k}: {v}" for k, v in rs.get("fault_reps", {}).items())
            lines.append(f'<div class="rep-summary">📋 <strong>Rep breakdown:</strong> {rs.get("valid_reps","?")} valid reps &nbsp;|&nbsp; {fault_reps}</div>')
        lines.append('</div>')

    feedback = data.get("feedback", {})
    param_labels = {
        "posture": "Posture",
        "stability": "Stability",
        "movement_quality": "Movement Quality",
        "range_of_motion": "Range of Motion",
    }
    for key, label in param_labels.items():
        fb = feedback.get(key, {})
        if not fb:
            continue
        obs = fb.get("critical_observations")
        obs_html = f'<div class="obs">⚠️ {obs}</div>' if obs else '<div class="obs-none">✅ No issues identified</div>'
        lines.append(f"""
        <div class="param">
          <div class="param-header">{label}</div>
          <div class="doing-well-inline">✅ {fb.get("doing_well","")}</div>
          {obs_html}
          <div class="rec">→ {fb.get("recommendation","")}</div>
        </div>""")

    return "\n".join(lines)


def generate_html(results: list[dict]) -> str:
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #f4f6f9; color: #1a1a2e; padding: 32px 20px; }
    .page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }
    .page-sub   { font-size: 14px; color: #666; margin-bottom: 8px; }
    .question   { background: #1a1a2e; color: #fff; padding: 14px 20px;
                  border-radius: 10px; font-size: 15px; font-weight: 600;
                  margin-bottom: 32px; }
    .video-block { margin-bottom: 48px; }
    .video-title { font-size: 17px; font-weight: 700; color: #333;
                   border-left: 4px solid #4472C4; padding-left: 12px;
                   margin-bottom: 16px; }
    .formats     { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .format-col  { background: #fff; border-radius: 12px; padding: 20px;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .format-label { font-size: 13px; font-weight: 700; text-transform: uppercase;
                    letter-spacing: 0.5px; color: #fff; padding: 4px 12px;
                    border-radius: 6px; display: inline-block; margin-bottom: 14px; }
    .label-a { background: #4472C4; }
    .label-b { background: #7030A0; }
    .verdict  { background: #f0f4ff; border-left: 3px solid #4472C4;
                padding: 12px 14px; border-radius: 6px; font-size: 14px;
                line-height: 1.6; margin-bottom: 16px; }
    .issue    { border: 1px solid #e8ecf0; border-radius: 8px; padding: 14px;
                margin-bottom: 12px; }
    .issue-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .rank     { background: #1a1a2e; color: #fff; border-radius: 50%;
                width: 24px; height: 24px; display: flex; align-items: center;
                justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
    .issue-label { font-weight: 600; font-size: 15px; }
    .issue-type  { font-size: 11px; background: #f0f0f0; padding: 2px 8px;
                   border-radius: 10px; color: #555; }
    .chain    { font-size: 12px; color: #7030A0; margin: 2px 0 4px 34px; }
    .issue-meta { display: flex; gap: 16px; font-size: 12px; color: #555;
                  margin: 8px 0; flex-wrap: wrap; }
    .trend-bad  { color: #c00; font-weight: 600; }
    .trend-ok   { color: #888; }
    .trend-good { color: #2e7d32; font-weight: 600; }
    .severity { font-size: 12px; color: #444; background: #f9f9f9;
                padding: 4px 8px; border-radius: 4px; margin: 6px 0; }
    .rec      { font-size: 13px; color: #1a1a2e; font-weight: 500;
                border-top: 1px solid #f0f0f0; padding-top: 8px; margin-top: 8px; }
    .doing-well { background: #f0faf0; border-radius: 6px; padding: 10px 14px;
                  font-size: 13px; margin-top: 12px; }
    .doing-well ul { padding-left: 18px; margin-top: 4px; }
    .doing-well li { margin-bottom: 4px; color: #2e7d32; }
    .analysis-block { background: #faf5ff; border: 1px solid #e0d0f0;
                      border-radius: 8px; padding: 14px; margin-bottom: 14px; }
    .causal-chain { font-size: 14px; font-weight: 600; color: #7030A0; margin-bottom: 6px; }
    .chain-explain { font-size: 13px; color: #555; margin-bottom: 8px; line-height: 1.5; }
    .trends, .asym, .rep-summary { font-size: 12px; color: #444; margin-bottom: 4px; }
    .param    { border: 1px solid #e8ecf0; border-radius: 8px; padding: 14px;
                margin-bottom: 10px; }
    .param-header { font-weight: 700; font-size: 14px; color: #333; margin-bottom: 8px; }
    .doing-well-inline { font-size: 12px; color: #2e7d32; margin-bottom: 6px; }
    .obs      { font-size: 13px; color: #c00; background: #fff5f5;
                padding: 8px 10px; border-radius: 4px; margin: 6px 0; }
    .obs-none { font-size: 12px; color: #888; margin: 4px 0; }
    .rating   { margin-top: 16px; padding: 12px; background: #fffbf0;
                border: 1px dashed #ddd; border-radius: 8px; font-size: 13px; color: #555; }
    @media (max-width: 700px) { .formats { grid-template-columns: 1fr; } }
    """

    blocks = []
    for r in results:
        vid   = r["video_id"]
        fault = FAULT_LABELS.get(vid, "")
        a_html = format_option_a(r["option_a"])
        b_html = format_option_b(r["option_b"])
        blocks.append(f"""
        <div class="video-block">
          <div class="video-title">{vid} — {fault}</div>
          <div class="formats">
            <div class="format-col">
              <div class="format-label label-a">Format 1</div>
              {a_html}
            </div>
            <div class="format-col">
              <div class="format-label label-b">Format 2</div>
              {b_html}
            </div>
          </div>
          <div class="rating">
            <strong>Your rating:</strong> &nbsp;
            ☐ Format 1 tells me more clearly what to fix &nbsp;&nbsp;
            ☐ Format 2 tells me more clearly what to fix &nbsp;&nbsp;
            ☐ Both equally clear &nbsp;&nbsp;
            Notes: ____________________________________
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kinetic AI — Coaching Format Feedback</title>
<style>{css}</style>
</head>
<body>
<div class="page-title">Kinetic AI — Coaching Format Review</div>
<div class="page-sub">3 squat analyses, 2 formats each. All outputs generated from the same data.</div>
<div class="question">
  ❓ For each video below: <strong>which format tells you more clearly what to fix?</strong>
</div>
{''.join(blocks)}
</body>
</html>"""


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY not set.")

    all_results = []

    for vid_id in VIDEO_IDS:
        print(f"\n{'─'*50}")
        print(f"  {vid_id} — {FAULT_LABELS[vid_id]}")
        print(f"{'─'*50}")

        mp_json = json.loads(JSON_FILES[vid_id].read_text())
        video_path = VIDEO_FILES[vid_id]

        print(f"  Option A (Priority Issues)...", end=" ", flush=True)
        try:
            out_a, lat_a = run(mp_json, video_path, OPTION_A_SCHEMA, "Option A")
            print(f"✅ {lat_a/1000:.1f}s")
        except Exception as e:
            print(f"ERROR — {e}")
            out_a = {}

        print(f"  Option B (Analysis + Parameters)...", end=" ", flush=True)
        try:
            out_b, lat_b = run(mp_json, video_path, OPTION_B_SCHEMA, "Option B")
            print(f"✅ {lat_b/1000:.1f}s")
        except Exception as e:
            print(f"ERROR — {e}")
            out_b = {}

        all_results.append({
            "video_id": vid_id,
            "fault": FAULT_LABELS[vid_id],
            "option_a": out_a,
            "option_b": out_b,
        })

    # Write raw JSON
    raw_path = OUT_DIR / "raw_outputs.json"
    raw_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n  → {raw_path}")

    # Write HTML
    html_path = OUT_DIR / "format_comparison.html"
    html_path.write_text(generate_html(all_results))
    print(f"  → {html_path}")
    print(f"\nOpen in browser: open {html_path}")


if __name__ == "__main__":
    main()
