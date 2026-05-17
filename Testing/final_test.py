#!/usr/bin/env python3
"""
Kinetic AI — Final Architecture Test
5 variants across 6 standardised goblet squat videos.

Single-LLM (analysis + coaching in one call):
  S1 — Sonnet 4.6     — JSON + 8 frames (original)
  S2 — Haiku 4.5      — JSON + 8 frames (original)
  S3 — Gemini 2.5 Flash — JSON + full processed video (skeleton overlay)

Two-LLM (analysis model → Sonnet coaching):
  S4 — Haiku → Sonnet   — Haiku: JSON + 8 frames → Sonnet: analysis JSON only
  S5 — Gemini → Sonnet  — Gemini: JSON + processed video → Sonnet: analysis JSON only

Output: final_results/scores.csv
        final_results/feedback_for_rating.md
        final_results/raw_outputs.json

Usage:
  export ANTHROPIC_API_KEY=your_key
  export GOOGLE_API_KEY=your_key
  python final_test.py
"""

import os, re, json, time, base64, csv, math, warnings
import cv2
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path

warnings.filterwarnings("ignore")

import anthropic
import google.generativeai as genai

# ── CONFIG ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")

SONNET = "claude-sonnet-4-6"
HAIKU  = "claude-haiku-4-5-20251001"
GEMINI = "gemini-2.5-flash"

FRAMES_PER_VIDEO = 8

VIDEOS_DIR           = Path("videos")
PROCESSED_VIDEOS_DIR = Path("processed_videos")
JSON_DIR             = Path("json")
RESULTS_DIR          = Path("final_results")
RESULTS_DIR.mkdir(exist_ok=True)

GROUND_TRUTH = {
    "V1": {"insufficient_depth": True,  "knee_valgus": None,  "excessive_forward_lean": None},
    "V2": {"insufficient_depth": False, "knee_valgus": None,  "excessive_forward_lean": None},
    "V3": {"insufficient_depth": None,  "knee_valgus": True,  "excessive_forward_lean": None},
    "V4": {"insufficient_depth": None,  "knee_valgus": False, "excessive_forward_lean": None},
    "V5": {"insufficient_depth": None,  "knee_valgus": None,  "excessive_forward_lean": True},
    "V6": {"insufficient_depth": None,  "knee_valgus": None,  "excessive_forward_lean": False},
}

VIDEO_FILES = {
    "V1": VIDEOS_DIR / "v1_depth_fault.mp4",
    "V2": VIDEOS_DIR / "v2_depth_good.mp4",
    "V3": VIDEOS_DIR / "v3_knee_fault.mp4",
    "V4": VIDEOS_DIR / "v4_knee_good.mp4",
    "V5": VIDEOS_DIR / "v5_torso_fault.mp4",
    "V6": VIDEOS_DIR / "v6_torso_good.mp4",
}

PROCESSED_VIDEO_FILES = {
    "V1": PROCESSED_VIDEOS_DIR / "v1_depth_fault_processed.mp4",
    "V2": PROCESSED_VIDEOS_DIR / "v2_depth_good_processed.mp4",
    "V3": PROCESSED_VIDEOS_DIR / "v3_knee_fault_processed.mp4",
    "V4": PROCESSED_VIDEOS_DIR / "v4_knee_good_processed.mp4",
    "V5": PROCESSED_VIDEOS_DIR / "v5_torso_fault_processed.mp4",
    "V6": PROCESSED_VIDEOS_DIR / "v6_torso_good_processed.mp4",
}

JSON_FILES = {k: JSON_DIR / f"v{i+1}.json" for i, k in enumerate(["V1","V2","V3","V4","V5","V6"])}

# ── SHARED CONTEXT ────────────────────────────────────────────────────────────

MOVEMENT_CONTEXT = """
## Movement Context
GOBLET SQUAT — weight held at chest height.
- Torso upright; slight forward lean acceptable, no slouching
- Hip crease at or below knee = sufficient depth
- Excessive lean signals a mobility or technique issue
"""

ANGLE_CONVENTION = """
## Angle Convention
MediaPipe interior angles: knee_angle/hip_angle DECREASE as flexion increases.
  Lower knee_angle = deeper squat. Lower hip_angle = more hip flexion.
All other angles (back_angle, valgus, foot_angle) compare directly.
When comparing visual to JSON for knee/hip: convert (MediaPipe = 180° − flexion), ±10° tolerance.
"""

ANALYSIS_RULES = """
## Analysis Rules
- Walk-in/walk-out: if first or last rep duration ≥ 3× median, include in rep_count
  but exclude entirely from all analysis.
- Valgus: ignore valgus_flag boolean. Use knee_valgus_distance per rep.
  Flag knee_valgus only if ≥ 50% of valid reps have distance < 0.22.
- For every issue: state how many valid reps show it (X of Y), which rep numbers,
  trend direction and magnitude, and actual measured values.
- Bilateral check: compare foot_turnout_left vs foot_turnout_right — flag if gap > 10°.
- Causal chain: if multiple issues co-exist, identify root cause and chain them.
"""

# ── STEP 1 ANALYSIS PROMPT (for S4 and S5) ───────────────────────────────────

ANALYSIS_SYSTEM = (
    "You are a biomechanics analyst. Return structured analysis JSON only. "
    "Respond ONLY in valid JSON. No prose outside the JSON."
)

ANALYSIS_SCHEMA = """
## Output — Structured Analysis
{
  "rep_count": <integer>,
  "valid_reps": <integer>,
  "walk_in_out_excluded": ["<rep + reason>"],
  "faults_detected": {
    "insufficient_depth": <true|false>,
    "knee_valgus": <true|false>,
    "excessive_forward_lean": <true|false>
  },
  "confidence": {
    "insufficient_depth": <0.0-1.0>,
    "knee_valgus": <0.0-1.0>,
    "excessive_forward_lean": <0.0-1.0>
  },
  "fault_detail": {
    "insufficient_depth": {
      "present": <true|false>,
      "reps_affected": "<X of Y>",
      "which_reps": [<rep numbers>],
      "severity": "<actual value e.g. knee_angle_min 117.57°>",
      "trend": "<stable|improving|worsening +X/rep>",
      "source": "<json|visual|both>"
    },
    "knee_valgus": {
      "present": <true|false>,
      "reps_affected": "<X of Y>",
      "which_reps": [<rep numbers>],
      "severity": "<knee_valgus_distance values>",
      "valgus_phase": "<EARLY|MID|LATE>",
      "trend": "<stable|improving|worsening>",
      "source": "<json|visual|both>"
    },
    "excessive_forward_lean": {
      "present": <true|false>,
      "reps_affected": "<X of Y>",
      "which_reps": [<rep numbers>],
      "severity": "<back_angle values>",
      "breakdown_timing": "<when in descent lean begins>",
      "trend": "<stable|improving|worsening +X/rep>",
      "source": "<json|visual|both>"
    }
  },
  "causal_chain": {
    "root_cause": "<most impactful issue or null>",
    "chain": "<e.g. ankle restriction → forward lean → depth deficit, or null>",
    "explanation": "<1-2 sentences on biomechanical relationship>"
  },
  "trends": {
    "worsening": ["<metric + direction + magnitude>"],
    "improving": ["<metric>"],
    "stable": ["<metric>"]
  },
  "rep_progression": "<2-3 sentences on how form evolved from rep 1 to last rep across all parameters>",
  "asymmetry_flags": ["<L/R difference >10° if present>"]
}

CRITICAL: faults_detected must be an OBJECT with three boolean keys, not an array.
Return raw JSON only — no markdown fences.
"""

def build_analysis_prompt(mediapipe_json: dict, visual_context: str) -> str:
    return f"""{visual_context}
{ANGLE_CONVENTION}
{MOVEMENT_CONTEXT}
## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}
{ANALYSIS_RULES}
{ANALYSIS_SCHEMA}"""


# ── COACHING OUTPUT SCHEMA ────────────────────────────────────────────────────

COACHING_SYSTEM = (
    "You are a sports coach writing concise feedback for a fitness app. "
    "Respond ONLY in valid JSON. No prose outside the JSON."
)

COACHING_SCHEMA = """
## Output — Coaching Response
{
  "total_score": <0-100 — overall form score. Start from 100 and deduct based on faults found:
                  significant fault = -20 to -25, moderate = -10 to -15, minor = -5.
                  If no faults, score should reflect technique quality (consistency, tempo etc).>,

  "verdict": "<2-4 sentences. Second person. Overall assessment of their form this session.
               Lead with the most important finding. If a causal chain exists, name it.>",

  "positive_observations": [
    {
      "observation": "<specific — name the rep numbers, how many reps, actual metric value>",
      "category": "<Posture | Stability | Movement Quality | Range of Motion>"
    }
  ],
  // maximum 3 items, most impactful first

  "critical_observations": [
    {
      "observation": "<specific — rep numbers, how many reps, measured value, worsening trend if any>",
      "category": "<Posture | Stability | Movement Quality | Range of Motion>",
      "type": "<root_cause | symptom>",
      "caused_by": "<name of root cause if this is a symptom, else null>"
    }
  ],
  // maximum 3 items, ordered by severity — most severe first
  // if causal chain exists: root_cause item must come before its symptoms

  "recommendation": "<If causal chain: state it clearly (e.g. fix ankle mobility first — it is causing the lean and the depth deficit). Then state 1-2 specific things to do in the NEXT workout: named drill, reps, sets.>",

  "rep_trend": {
    "observation": "<2-3 sentences on how form evolved from rep 1 to the last rep. Reference specific parameters that changed — did lean worsen, did depth improve, did tempo slow? Be specific.>",
    "recommendation": "<1 sentence on the single most important thing to focus on next session based on this trend.>"
  }
}
"""

def build_coaching_from_analysis(analysis: dict) -> str:
    return f"""## Biomechanics Analysis
{json.dumps(analysis, indent=2)}

## Your Task
Write concise coaching feedback based solely on this analysis.
- Reference specific rep numbers, counts, and measured values throughout
- If a causal chain is identified in the analysis, reflect it clearly in critical_observations
  (root_cause item first, then its symptoms) and in the recommendation
- total_score must reflect the severity and number of faults found
- positive_observations: only include if genuinely present — do not invent positives
- critical_observations: ordered most severe first, max 3
- rep_trend.observation must reference the actual trend data from the analysis

{MOVEMENT_CONTEXT}
{COACHING_SCHEMA}"""

def build_single_llm_prompt(mediapipe_json: dict, visual_context: str) -> str:
    return f"""{visual_context}
{ANGLE_CONVENTION}
{MOVEMENT_CONTEXT}
## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}
{ANALYSIS_RULES}

## Your Task
Analyse the squat data and produce a coaching response.
Apply all analysis rules above: rep counts, trends, bilateral check, causal chain.

{COACHING_SCHEMA}

Also include these analysis fields at the top of your JSON (before total_score):
  "faults_detected": {{"insufficient_depth": <bool>, "knee_valgus": <bool>, "excessive_forward_lean": <bool>}},
  "confidence": {{"insufficient_depth": <0.0-1.0>, "knee_valgus": <0.0-1.0>, "excessive_forward_lean": <0.0-1.0>}},
  "evidence_source": "<json|visual|both — dominant source for fault calls>",
"""


# ── UTILITIES ─────────────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if fence:
        raw = fence.group(1)
    return json.loads(raw)

def extract_frames(video_path: Path, n: int = FRAMES_PER_VIDEO) -> list[str]:
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_b64 = []
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i * total / n))
        ret, frame = cap.read()
        if ret:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames_b64.append(base64.b64encode(buf).decode())
    cap.release()
    return frames_b64

def build_composite(frames_b64: list[str], cols: int = 4) -> str:
    frames = []
    for b64 in frames_b64:
        arr = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
        if arr is not None:
            frames.append(arr)
    rows = math.ceil(len(frames) / cols)
    h, w = frames[0].shape[:2]
    tw, th = min(w, 320), min(h, 240)
    grid_rows = []
    for r in range(rows):
        row_frames = frames[r*cols:(r+1)*cols]
        while len(row_frames) < cols:
            row_frames.append(np.zeros((th, tw, 3), dtype=np.uint8))
        grid_rows.append(np.hstack([cv2.resize(f, (tw, th)) for f in row_frames]))
    grid = np.vstack(grid_rows)
    _, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode()

def gemini_upload(video_path: Path):
    print("      uploading...", end=" ", flush=True)
    vf = genai.upload_file(path=str(video_path))
    while vf.state.name == "PROCESSING":
        time.sleep(2)
        vf = genai.get_file(vf.name)
    print("ready", end=" ", flush=True)
    return vf

def gemini_delete(vf):
    try: genai.delete_file(vf.name)
    except: pass


# ── VARIANT RUNNERS ───────────────────────────────────────────────────────────

def run_s1_sonnet(mp_json: dict, vid: str) -> tuple[dict, float, float]:
    """S1: Sonnet end-to-end — JSON + 8 frames (original)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    frames    = extract_frames(VIDEO_FILES[vid])
    composite = build_composite(frames)
    prompt    = build_single_llm_prompt(mp_json, f"Attached: composite grid of {len(frames)} frames from original squat video.")
    start = time.time()
    resp = client.messages.create(
        model=SONNET, max_tokens=1500, system=COACHING_SYSTEM,
        messages=[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":composite}},
            {"type":"text","text":prompt},
        ]}],
    )
    lat = (time.time()-start)*1000
    return extract_json(resp.content[0].text), lat, 0.0


def run_s2_haiku(mp_json: dict, vid: str) -> tuple[dict, float, float]:
    """S2: Haiku end-to-end — JSON + 8 frames (original)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    frames    = extract_frames(VIDEO_FILES[vid])
    composite = build_composite(frames)
    prompt    = build_single_llm_prompt(mp_json, f"Attached: composite grid of {len(frames)} frames from original squat video.")
    schema_reminder = (
        "\n\nCRITICAL: Return ONLY a valid JSON object matching the schema above. "
        "faults_detected must be an OBJECT with three boolean keys — not an array. "
        "No markdown fences, no extra text outside the JSON."
    )
    start = time.time()
    resp = client.messages.create(
        model=HAIKU, max_tokens=2000, system=COACHING_SYSTEM,
        messages=[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":composite}},
            {"type":"text","text":prompt + schema_reminder},
        ]}],
    )
    if resp.stop_reason == "max_tokens":
        raise ValueError("Haiku truncated — increase max_tokens")
    lat = (time.time()-start)*1000
    return extract_json(resp.content[0].text), lat, 0.0


def run_s3_gemini(mp_json: dict, vid: str) -> tuple[dict, float, float]:
    """S3: Gemini end-to-end — JSON + full processed video (skeleton overlay)."""
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(GEMINI)
    vf    = gemini_upload(PROCESSED_VIDEO_FILES[vid])
    prompt = build_single_llm_prompt(
        mp_json,
        "Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. "
        "Green lines indicate detected joint positions."
    )
    start = time.time()
    resp = model.generate_content(
        [prompt, vf],
        generation_config={"temperature":0.1,"response_mime_type":"application/json"},
    )
    lat = (time.time()-start)*1000
    gemini_delete(vf)
    return extract_json(resp.text), lat, 0.0


def run_s4_haiku_sonnet(mp_json: dict, vid: str) -> tuple[dict, float, float]:
    """S4: Haiku analyses → Sonnet coaches."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Haiku analysis
    frames    = extract_frames(VIDEO_FILES[vid])
    composite = build_composite(frames)
    visual    = f"Attached: composite grid of {len(frames)} frames from original squat video."
    prompt1   = build_analysis_prompt(mp_json, visual)
    schema_reminder = (
        "\n\nCRITICAL: Return ONLY the JSON object from the Output schema. "
        "faults_detected must be an OBJECT with three boolean keys, not an array. "
        "No markdown fences, no extra text."
    )
    start1 = time.time()
    r1 = client.messages.create(
        model=HAIKU, max_tokens=2500, system=ANALYSIS_SYSTEM,
        messages=[{"role":"user","content":[
            {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":composite}},
            {"type":"text","text":prompt1+schema_reminder},
        ]}],
    )
    if r1.stop_reason == "max_tokens":
        raise ValueError("Haiku analysis truncated")
    lat1 = (time.time()-start1)*1000
    analysis = extract_json(r1.content[0].text)

    # Step 2: Sonnet coaching
    start2 = time.time()
    r2 = client.messages.create(
        model=SONNET, max_tokens=1500, system=COACHING_SYSTEM,
        messages=[{"role":"user","content":build_coaching_from_analysis(analysis)}],
    )
    lat2 = (time.time()-start2)*1000

    coaching = extract_json(r2.content[0].text)
    coaching["_analysis"] = analysis  # store for reporting
    return coaching, lat1, lat2


def run_s5_gemini_sonnet(mp_json: dict, vid: str) -> tuple[dict, float, float]:
    """S5: Gemini analyses → Sonnet coaches."""
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Gemini analysis
    vf = gemini_upload(PROCESSED_VIDEO_FILES[vid])
    visual = ("Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. "
              "Green lines indicate detected joint positions.")
    prompt1 = build_analysis_prompt(mp_json, visual)
    start1  = time.time()
    r1 = gemini_model.generate_content(
        [prompt1, vf],
        generation_config={"temperature":0.1,"response_mime_type":"application/json"},
    )
    lat1 = (time.time()-start1)*1000
    gemini_delete(vf)
    analysis = extract_json(r1.text)

    # Step 2: Sonnet coaching
    start2 = time.time()
    r2 = client.messages.create(
        model=SONNET, max_tokens=1500, system=COACHING_SYSTEM,
        messages=[{"role":"user","content":build_coaching_from_analysis(analysis)}],
    )
    lat2 = (time.time()-start2)*1000

    coaching = extract_json(r2.content[0].text)
    coaching["_analysis"] = analysis
    return coaching, lat1, lat2


# ── RESULT ───────────────────────────────────────────────────────────────────

@dataclass
class Result:
    video_id:      str
    variant:       str
    model_label:   str
    fault_key:     str
    ground_truth:  bool
    prediction:    bool
    correct:       bool
    confidence:    float
    evidence_src:  str
    total_score:   int
    analysis_lat:  float
    coaching_lat:  float
    total_lat:     float
    verdict:       str
    positives:     list
    criticals:     list
    recommendation:str
    rep_trend:     dict
    raw_output:    dict
    error:         str = ""


def score_result(vid: str, variant: str, model_label: str,
                 output: dict, lat1: float, lat2: float) -> Result:
    gt        = GROUND_TRUTH[vid]
    fault_key = next(k for k, v in gt.items() if v is not None)
    gt_val    = gt[fault_key]
    predicted = (output.get("faults_detected") or {}).get(fault_key)
    confidence= (output.get("confidence") or {}).get(fault_key, -1.0)

    return Result(
        video_id      = vid,
        variant       = variant,
        model_label   = model_label,
        fault_key     = fault_key,
        ground_truth  = gt_val,
        prediction    = predicted,
        correct       = (predicted == gt_val),
        confidence    = confidence,
        evidence_src  = output.get("evidence_source",""),
        total_score   = output.get("total_score", -1),
        analysis_lat  = round(lat1, 1),
        coaching_lat  = round(lat2, 1),
        total_lat     = round(lat1+lat2, 1),
        verdict       = output.get("verdict",""),
        positives     = output.get("positive_observations") or [],
        criticals     = output.get("critical_observations") or [],
        recommendation= output.get("recommendation",""),
        rep_trend     = output.get("rep_trend") or {},
        raw_output    = output,
    )


# ── REPORTING ─────────────────────────────────────────────────────────────────

def write_csv(results: list[Result]):
    path = RESULTS_DIR / "scores.csv"
    with open(path,"w",newline="") as f:
        w = csv.writer(f)
        w.writerow(["Video","Variant","Models","Fault","GT","Prediction","Correct",
                    "Confidence","Src","Score/100","Analysis(ms)","Coaching(ms)","Total(ms)","Error"])
        for r in results:
            w.writerow([r.video_id,r.variant,r.model_label,r.fault_key,
                        r.ground_truth,r.prediction,"✅" if r.correct else "❌",
                        f"{r.confidence:.2f}" if r.confidence>=0 else "N/A",
                        r.evidence_src, r.total_score if r.total_score>=0 else "N/A",
                        r.analysis_lat,r.coaching_lat,r.total_lat,r.error])
    print(f"  → {path}")


def write_feedback_md(results: list[Result]):
    path = RESULTS_DIR / "feedback_for_rating.md"
    lines = [
        "# Kinetic AI — PT Coaching Quality Review\n\n",
        "**Question:** How well does each response tell the athlete what to fix and how?\n\n",
        "| Score | Criteria |\n|---|---|\n",
        "| 5 | Specific, accurate, names reps and trends, clear causal chain, actionable drill |\n",
        "| 4 | Accurate, slightly generic — right issue, vague cue |\n",
        "| 3 | Partially correct — real issue but rep context or trend missing |\n",
        "| 2 | Inaccurate — wrong fault or contradicts data |\n",
        "| 1 | Missing when fault clearly present |\n\n---\n\n",
    ]
    import random; random.seed(99)
    by_video = {}
    for r in results:
        by_video.setdefault(r.video_id,[]).append(r)

    entry_num = 1
    for vid in ["V1","V2","V3","V4","V5","V6"]:
        vr = by_video.get(vid,[])
        random.shuffle(vr)
        for r in vr:
            if r.error: continue
            lines.append(f"## Entry {entry_num} — {vid} | {r.fault_key}\n")
            lines.append(f"<!-- Variant: {r.variant} | {r.model_label} -->\n\n")
            lines.append(f"**Score given by model: {r.total_score}/100**\n\n")
            lines.append(f"**Verdict:** {r.verdict}\n\n")

            if r.positives:
                lines.append("**What's working:**\n")
                for p in r.positives:
                    lines.append(f"- [{p.get('category','')}] {p.get('observation','')}\n")
                lines.append("\n")

            if r.criticals:
                lines.append("**Needs attention:**\n")
                for c in r.criticals:
                    ctype = f" ({c.get('type','')})" if c.get('type') else ""
                    cause = f" ← caused by: {c.get('caused_by')}" if c.get('caused_by') else ""
                    lines.append(f"- [{c.get('category','')}]{ctype}{cause}: {c.get('observation','')}\n")
                lines.append("\n")

            lines.append(f"**Recommendation:** {r.recommendation}\n\n")

            rt = r.rep_trend
            if rt:
                lines.append(f"**Rep trend:** {rt.get('observation','')}  \n")
                lines.append(f"→ {rt.get('recommendation','')}\n\n")

            lines.append(f"**PT Rating (1–5):** ___\n\n---\n\n")
            entry_num += 1

    path.write_text("".join(lines))
    print(f"  → {path}")


def write_raw(results: list[Result]):
    path = RESULTS_DIR / "raw_outputs.json"
    path.write_text(json.dumps([vars(r) for r in results], indent=2, default=str))
    print(f"  → {path}")


def print_summary(results: list[Result]):
    variants = ["S1","S2","S3","S4","S5"]
    labels   = {"S1":"Sonnet","S2":"Haiku","S3":"Gemini","S4":"Haiku→Sonnet","S5":"Gemini→Sonnet"}
    print("\n" + "="*65)
    print("  FINAL TEST — RESULTS")
    print("="*65)
    for v in variants:
        vr = [r for r in results if r.variant==v and not r.error]
        if not vr: continue
        correct = sum(1 for r in vr if r.correct)
        t_lats  = [r.total_lat for r in vr if r.total_lat>0 and r.total_lat<120000]
        scores  = [r.total_score for r in vr if r.total_score>=0]
        print(f"\n  {v} — {labels[v]}")
        print(f"    Accuracy:     {correct}/{len(vr)}")
        print(f"    Avg latency:  {round(sum(t_lats)/len(t_lats)/1000,1) if t_lats else '—'}s")
        print(f"    Avg score:    {round(sum(scores)/len(scores)) if scores else '—'}/100")
        wrong = [r for r in vr if not r.correct]
        if wrong:
            for r in wrong:
                print(f"    ⚠️  {r.video_id} | expected={r.ground_truth} got={r.prediction} conf={r.confidence:.2f}")
    print("\n" + "="*65)


# ── MAIN ─────────────────────────────────────────────────────────────────────

VARIANTS = [
    ("S1", "Sonnet 4.6 (end-to-end)",          run_s1_sonnet),
    ("S2", "Haiku 4.5 (end-to-end)",            run_s2_haiku),
    ("S3", "Gemini 2.5 Flash (end-to-end)",     run_s3_gemini),
    ("S4", "Haiku 4.5 → Sonnet 4.6",            run_s4_haiku_sonnet),
    ("S5", "Gemini 2.5 Flash → Sonnet 4.6",     run_s5_gemini_sonnet),
]


def main():
    if not ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY not set.")
    if not GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY not set.")

    all_results: list[Result] = []

    for variant, label, runner in VARIANTS:
        print(f"\n{'─'*55}")
        print(f"  {variant} — {label}")
        print(f"{'─'*55}")

        for vid in GROUND_TRUTH:
            print(f"  {vid} ...", end=" ", flush=True)
            if not JSON_FILES[vid].exists():
                print("SKIP — JSON not found"); continue
            mp_json = json.loads(JSON_FILES[vid].read_text())
            try:
                output, lat1, lat2 = runner(mp_json, vid)
                r = score_result(vid, variant, label, output, lat1, lat2)
                all_results.append(r)
                score_str = f"score={r.total_score}" if r.total_score>=0 else ""
                print(f"{'✅' if r.correct else '❌'}  {r.total_lat/1000:.1f}s  {score_str}")
            except Exception as exc:
                print(f"ERROR — {exc}")
                gt = GROUND_TRUTH[vid]
                fk = next(k for k,v in gt.items() if v is not None)
                all_results.append(Result(
                    video_id=vid,variant=variant,model_label=label,
                    fault_key=fk,ground_truth=gt[fk],prediction=False,
                    correct=False,confidence=-1,evidence_src="",total_score=-1,
                    analysis_lat=0,coaching_lat=0,total_lat=0,
                    verdict="",positives=[],criticals=[],recommendation="",
                    rep_trend={},raw_output={},error=str(exc),
                ))

    print("\nWriting outputs...")
    write_csv(all_results)
    write_feedback_md(all_results)
    write_raw(all_results)
    print_summary(all_results)


if __name__ == "__main__":
    main()
