#!/usr/bin/env python3
"""
Kinetic AI — 2-LLM Pipeline Test
Tests 3 architectures for squat form analysis + coaching:

  Option 1 — Sonnet end-to-end       (fresh run with updated prompts)
  Option 2 — Gemini Flash → Sonnet   (Gemini analyses, Sonnet coaches)
  Option 3 — Claude Haiku → Sonnet   (Haiku analyses, Sonnet coaches)

In Options 2 and 3:
  Step 1 model reads JSON + video/frames → outputs structured analysis only
  Step 2 (Sonnet) reads Step 1 output (text only) → outputs coaching

Outputs:
  pipeline_results/scores.csv
  pipeline_results/feedback_for_rating.md
  pipeline_results/raw_outputs.json

Usage:
  export ANTHROPIC_API_KEY=your_key
  export GOOGLE_API_KEY=your_key
  python pipeline_test.py
"""

import os, re, json, time, base64, csv, warnings
import cv2
from dataclasses import dataclass, field
from pathlib import Path

warnings.filterwarnings("ignore")

import anthropic
import google.generativeai as genai

# ── CONFIG ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")

ANALYSIS_MODEL_GEMINI = "gemini-2.5-flash"
ANALYSIS_MODEL_HAIKU  = "claude-haiku-4-5-20251001"
COACHING_MODEL        = "claude-sonnet-4-6"

FRAMES_PER_VIDEO = 8

VIDEOS_DIR           = Path("videos")
PROCESSED_VIDEOS_DIR = Path("processed_videos")
JSON_DIR             = Path("json")
RESULTS_DIR          = Path("pipeline_results")
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

JSON_FILES = {
    "V1": JSON_DIR / "v1.json",
    "V2": JSON_DIR / "v2.json",
    "V3": JSON_DIR / "v3.json",
    "V4": JSON_DIR / "v4.json",
    "V5": JSON_DIR / "v5.json",
    "V6": JSON_DIR / "v6.json",
}

# Option 1 combined output schema (analysis + rich coaching in one call)
OPTION1_SCHEMA = """
## Output — Combined Analysis + Coaching (respond with this exact JSON)

{
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
  "evidence_source": "<json | visual | both | contradictory — overall dominant source>",

  "verdict": "<2-3 sentences. Action-oriented, second person. Most impactful fix first. Call out causal chain if multiple issues.>",

  "priority_fix": "<posture | stability | movement_quality | range_of_motion>",

  "next_session_focus": "<one specific drill or cue to begin the next session — a warm-up or pre-set action>",

  "feedback": {
    "posture": {
      "priority": <1-4>,
      "doing_well": "<specific — cite metric if positive>",
      "issue": {
        "present": <true|false>,
        "severity": "<minor | moderate | significant>",
        "reps_affected": "<X of Y valid reps, or null>",
        "trend": "<stable | improving | worsening +X/rep, or null>",
        "connected_to": "<parameter this is linked to, or null>"
      },
      "recommendation": {
        "cue": "<one short in-session cue>",
        "drill": "<named drill with reps/sets/timing>",
        "progress_check": "<how to know it is improving next session>"
      }
    },
    "stability": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {"present": <true|false>, "severity": "<minor|moderate|significant>",
                "reps_affected": "<X of Y or null>", "trend": "<or null>", "connected_to": "<or null>"},
      "recommendation": {"cue": "<cue>", "drill": "<drill with reps/sets>", "progress_check": "<signal>"}
    },
    "movement_quality": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {"present": <true|false>, "severity": "<minor|moderate|significant>",
                "reps_affected": "<X of Y or null>", "trend": "<or null>", "connected_to": "<or null>"},
      "recommendation": {"cue": "<cue>", "drill": "<drill with reps/sets>", "progress_check": "<signal>"}
    },
    "range_of_motion": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {"present": <true|false>, "severity": "<minor|moderate|significant>",
                "reps_affected": "<X of Y or null>", "trend": "<or null>", "connected_to": "<or null>"},
      "recommendation": {"cue": "<cue>", "drill": "<drill with reps/sets>", "progress_check": "<signal>"}
    }
  }
}
"""

OPTION1_SYSTEM = (
    "You are a biomechanics analyst and coach. Analyse the squat data then write coaching. "
    "Respond ONLY in valid JSON. No prose outside the JSON."
)

def build_option1_prompt(mediapipe_json: dict, n_frames: int) -> str:
    visual_context = f"Attached: a composite grid of {n_frames} frames sampled from the original squat video."
    return f"""{visual_context}

{ANGLE_CONVENTION}
{MOVEMENT_CONTEXT}

## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}

## Analysis Requirements
Before writing coaching, apply these analysis requirements:
- For every issue: state how many valid reps show it (X of Y), which rep numbers,
  trend direction and magnitude using JSON trend fields, and actual measured values
- Bilateral check: compare foot_turnout_left vs foot_turnout_right — flag if gap > 10°
- Causal chain: if multiple issues co-exist, identify root cause and chain them
  starting from most impactful. Do NOT list co-occurring faults as separate issues.

{SHARED_RULES}
{OPTION1_SCHEMA}"""

# ── SHARED CONTEXT ────────────────────────────────────────────────────────────

ANGLE_CONVENTION = """
## Angle Convention
MediaPipe interior angles: knee_angle/hip_angle DECREASE as flexion increases.
  - Lower knee_angle = deeper squat
  - Lower hip_angle = more hip flexion
All other angles (back_angle, valgus, foot_angle) compare directly.
When comparing visual to JSON for knee/hip: convert (MediaPipe = 180° − flexion), ±10° tolerance.
"""

MOVEMENT_CONTEXT = """
## Movement Context
GOBLET SQUAT — weight held at chest height.
- Torso upright; slight lean acceptable, no slouching
- Hip crease at or below knee = sufficient depth
- Excessive lean = mobility or technique issue
"""

SHARED_RULES = """
## Rules
- Walk-in/walk-out: if first or last rep duration ≥ 3× median, include in rep_count
  but exclude entirely from all analysis and feedback.
- Valgus: ignore valgus_flag boolean. Use knee_valgus_distance per rep.
  Flag knee_valgus only if ≥ 50% of valid reps have distance < 0.22.
"""

# ── STEP 1 PROMPT — ANALYSIS ONLY ────────────────────────────────────────────

ANALYSIS_SYSTEM = (
    "You are a biomechanics analyst. Analyse the squat data and return a structured "
    "analysis JSON. Respond ONLY in valid JSON. No prose outside the JSON."
)

ANALYSIS_SCHEMA = """
## Output — Structured Analysis (no coaching, no recommendations)
Return this exact JSON. Another model will write the coaching from your output.

{
  "rep_count": <integer — total including walk-in/out>,
  "valid_reps": <integer — excluding walk-in/out>,
  "walk_in_out_excluded": ["<rep number and reason if applicable>"],
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
      "reps_affected": "<X of Y valid reps>",
      "which_reps": [<rep numbers>],
      "severity": "<actual measured value e.g. knee_angle_min 117.57°>",
      "trend": "<stable|improving X/rep|worsening +X/rep>",
      "source": "<json|visual|both|contradictory>"
    },
    "knee_valgus": {
      "present": <true|false>,
      "reps_affected": "<X of Y valid reps>",
      "which_reps": [<rep numbers>],
      "severity": "<knee_valgus_distance values>",
      "valgus_phase": "<EARLY|MID|LATE — when in the rep collapse occurs>",
      "trend": "<stable|improving|worsening>",
      "source": "<json|visual|both|contradictory>"
    },
    "excessive_forward_lean": {
      "present": <true|false>,
      "reps_affected": "<X of Y valid reps>",
      "which_reps": [<rep numbers>],
      "severity": "<back_angle values at bottom>",
      "breakdown_timing": "<when in descent the lean begins>",
      "trend": "<stable|improving|worsening +X/rep>",
      "source": "<json|visual|both|contradictory>"
    }
  },
  "causal_chain": {
    "root_cause": "<most impactful issue — the one causing others, or null if single issue>",
    "chain": "<e.g. ankle restriction → forward lean → depth deficit, or null>",
    "explanation": "<1-2 sentences explaining the biomechanical relationship>"
  },
  "trends": {
    "worsening": ["<metric + direction + magnitude e.g. back_angle +0.9°/rep>"],
    "improving": ["<metric + direction>"],
    "stable": ["<metric>"]
  },
  "asymmetry_flags": ["<any L/R difference >10° e.g. foot_turnout L:29° R:12° — 17° gap>"],
  "source_conflicts": []
}
"""

def build_analysis_prompt(mediapipe_json: dict, visual_context: str) -> str:
    return f"""{visual_context}

{ANGLE_CONVENTION}
{MOVEMENT_CONTEXT}

## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}

{SHARED_RULES}
{ANALYSIS_SCHEMA}"""


# ── STEP 2 PROMPT — COACHING ONLY ────────────────────────────────────────────

COACHING_SYSTEM = (
    "You are a sports coach writing feedback for a fitness app user. "
    "You will receive a structured biomechanics analysis. Write actionable coaching. "
    "Respond ONLY in valid JSON. No prose outside the JSON."
)

COACHING_SCHEMA = """
## Output — Coaching Response

{
  "verdict": "<2-3 sentences. Action-oriented, second person. Start from the most impactful issue. If fixing one issue will resolve others downstream, say so explicitly.>",

  "priority_fix": "<posture | stability | movement_quality | range_of_motion — the single most important parameter to address>",

  "next_session_focus": "<one specific drill or cue to begin the very next session with — distinct from the recommendations below, framed as a warm-up or pre-set action>",

  "feedback": {
    "posture": {
      "priority": <1-4 — rank this parameter by urgency, 1 = most urgent>,
      "doing_well": "<specific and technical — cite actual metric if positive, e.g. 'back_angle_start consistently 15-20° across all reps'>",
      "issue": {
        "present": <true|false>,
        "severity": "<minor | moderate | significant>",
        "reps_affected": "<X of Y valid reps, or null if not present>",
        "trend": "<stable | improving | worsening +X/rep, or null>",
        "connected_to": "<parameter name this issue causes or is caused by, e.g. 'range_of_motion — ankle restriction drives this lean', or null>"
      },
      "recommendation": {
        "cue": "<one specific in-session cue — short enough to remember mid-set>",
        "drill": "<named drill with reps/sets/timing — always provide one even if it is the movement itself, e.g. 'goblet squat with 2s eccentric count, 3x5'>",
        "progress_check": "<how the user knows this is improving next session — measurable or observable signal>"
      }
    },
    "stability": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {
        "present": <true|false>,
        "severity": "<minor | moderate | significant>",
        "reps_affected": "<X of Y, or null>",
        "trend": "<stable | improving | worsening, or null>",
        "connected_to": "<or null>"
      },
      "recommendation": {
        "cue": "<in-session cue>",
        "drill": "<named drill with reps/sets>",
        "progress_check": "<observable signal>"
      }
    },
    "movement_quality": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {
        "present": <true|false>,
        "severity": "<minor | moderate | significant>",
        "reps_affected": "<X of Y, or null>",
        "trend": "<stable | improving | worsening, or null>",
        "connected_to": "<or null>"
      },
      "recommendation": {
        "cue": "<in-session cue>",
        "drill": "<named drill with reps/sets>",
        "progress_check": "<observable signal>"
      }
    },
    "range_of_motion": {
      "priority": <1-4>,
      "doing_well": "<specific>",
      "issue": {
        "present": <true|false>,
        "severity": "<minor | moderate | significant>",
        "reps_affected": "<X of Y, or null>",
        "trend": "<stable | improving | worsening, or null>",
        "connected_to": "<or null>"
      },
      "recommendation": {
        "cue": "<in-session cue>",
        "drill": "<named drill with reps/sets>",
        "progress_check": "<observable signal>"
      }
    }
  }
}
"""

def build_coaching_prompt(analysis_output: dict) -> str:
    return f"""## Biomechanics Analysis
The following structured analysis was produced by a specialist model:

{json.dumps(analysis_output, indent=2)}

## Your Task
Write coaching feedback based solely on this analysis. Do not re-derive faults.
- Reference specific values, rep counts, and trends from the analysis in every observation
- Apply the causal chain: if ankle restriction causes lean which causes depth deficit,
  address it as one connected problem in the verdict, starting from the root cause
- priority_fix must match the root cause identified in the analysis causal chain
- next_session_focus must be a concrete warm-up drill — not a repeat of recommendations below
- recommendation.drill must always be named with reps/sets/timing

{MOVEMENT_CONTEXT}
{COACHING_SCHEMA}"""


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
            import numpy as np
            row_frames.append(np.zeros((th, tw, 3), dtype=np.uint8))
        grid_rows.append(__import__("numpy").hstack([cv2.resize(f, (tw, th)) for f in row_frames]))
    grid = __import__("numpy").vstack(grid_rows)
    _, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode("utf-8")


# ── STEP 1 RUNNERS ────────────────────────────────────────────────────────────

def analyse_gemini(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """Step 1: Gemini analyses using full processed video."""
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(ANALYSIS_MODEL_GEMINI)

    print("      uploading to Gemini Files API...", end=" ", flush=True)
    video_file = genai.upload_file(path=str(video_path))
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    print("ready")

    visual_context = (
        "Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. "
        "Green lines indicate detected joint positions per frame."
    )
    prompt = build_analysis_prompt(mediapipe_json, visual_context)

    start = time.time()
    response = model.generate_content(
        [prompt, video_file],
        generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
    )
    latency_ms = (time.time() - start) * 1000

    try:
        genai.delete_file(video_file.name)
    except Exception:
        pass

    return extract_json(response.text), latency_ms


def analyse_haiku(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """Step 1: Haiku analyses using composite frame grid."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    frames = extract_frames(video_path)
    composite = build_composite(frames)
    visual_context = f"Attached: a composite grid of {len(frames)} frames sampled from the original squat video."
    prompt = build_analysis_prompt(mediapipe_json, visual_context)
    # Reinforce schema compliance — Haiku tends to invent its own format
    schema_reminder = (
        "\n\nCRITICAL: You MUST return ONLY the JSON object defined in the Output schema above. "
        "Do NOT invent new fields, arrays, or structures. "
        "faults_detected must be an OBJECT with three boolean keys, not an array. "
        "Return raw JSON only — no markdown fences, no extra text."
    )

    start = time.time()
    response = client.messages.create(
        model=ANALYSIS_MODEL_HAIKU,
        max_tokens=2500,  # increased from 1500 — schema JSON can exceed 1500 tokens
        system=ANALYSIS_SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": composite,
            }},
            {"type": "text", "text": prompt + schema_reminder},
        ]}],
    )
    latency_ms = (time.time() - start) * 1000
    raw = response.content[0].text
    if response.stop_reason == "max_tokens":
        raise ValueError(f"Haiku analysis truncated at max_tokens — increase limit or reduce prompt")
    return extract_json(raw), latency_ms


# ── STEP 2 RUNNER ─────────────────────────────────────────────────────────────

def coach_sonnet(analysis_output: dict) -> tuple[dict, float]:
    """Step 2: Sonnet writes coaching from analysis output (JSON only)."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = build_coaching_prompt(analysis_output)

    start = time.time()
    response = client.messages.create(
        model=COACHING_MODEL,
        max_tokens=1500,
        system=COACHING_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.content[0].text), latency_ms


# ── SCORING ───────────────────────────────────────────────────────────────────

@dataclass
class Result:
    video_id:            str
    option:              str
    analysis_model:      str
    coaching_model:      str
    rep_count:           int
    fault_key:           str
    ground_truth:        bool
    model_prediction:    bool
    correct:             bool
    confidence:          float
    evidence:            str
    evidence_source:     str
    analysis_latency_ms: float
    coaching_latency_ms: float
    total_latency_ms:    float
    verdict:             str
    priority_fix:        str
    next_session_focus:  str
    analysis_output:     dict
    feedback_posture:    dict
    feedback_stability:  dict
    feedback_movement:   dict
    feedback_rom:        dict
    error:               str = ""


def score(video_id: str, option: str, analysis_model: str,
          analysis_out: dict, coaching_out: dict,
          analysis_lat: float, coaching_lat: float) -> Result:
    gt        = GROUND_TRUTH[video_id]
    fault_key = next(k for k, v in gt.items() if v is not None)
    gt_val    = gt[fault_key]

    # Option 1: faults in combined output; Options 2/3: faults in analysis_out
    fault_source = coaching_out if option == "Option 1" else analysis_out
    predicted = fault_source.get("faults_detected", {}).get(fault_key)

    fd = analysis_out.get("fault_detail", {}).get(fault_key, {})
    evidence_obs = fd.get("severity", "")
    evidence_src = (fault_source.get("evidence_source", "") or
                    fd.get("source", ""))

    return Result(
        video_id            = video_id,
        option              = option,
        analysis_model      = analysis_model,
        coaching_model      = COACHING_MODEL,
        rep_count           = analysis_out.get("rep_count", coaching_out.get("rep_count", -1)),
        fault_key           = fault_key,
        ground_truth        = gt_val,
        model_prediction    = predicted,
        correct             = (predicted == gt_val),
        confidence          = fault_source.get("confidence", {}).get(fault_key, -1.0),
        evidence            = evidence_obs,
        evidence_source     = evidence_src,
        analysis_latency_ms = round(analysis_lat, 1),
        coaching_latency_ms = round(coaching_lat, 1),
        total_latency_ms    = round(analysis_lat + coaching_lat, 1),
        verdict             = coaching_out.get("verdict", ""),
        priority_fix        = coaching_out.get("priority_fix", ""),
        next_session_focus  = coaching_out.get("next_session_focus", ""),
        analysis_output     = analysis_out,
        feedback_posture    = coaching_out.get("feedback", {}).get("posture", {}),
        feedback_stability  = coaching_out.get("feedback", {}).get("stability", {}),
        feedback_movement   = coaching_out.get("feedback", {}).get("movement_quality", {}),
        feedback_rom        = coaching_out.get("feedback", {}).get("range_of_motion", {}),
    )


# ── REPORTING ─────────────────────────────────────────────────────────────────

def write_scores_csv(results: list[Result]):
    path = RESULTS_DIR / "scores.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Video", "Option", "Analysis Model", "Coaching Model",
            "Fault Tested", "Ground Truth", "Model Output", "Correct",
            "Confidence", "Evidence Source", "Priority Fix",
            "Analysis Latency (ms)", "Coaching Latency (ms)", "Total Latency (ms)",
            "Posture /5", "Stability /5", "Movement Quality /5", "Range of Motion /5", "Notes",
        ])
        for r in results:
            w.writerow([
                r.video_id, r.option, r.analysis_model, r.coaching_model,
                r.fault_key, r.ground_truth, r.model_prediction,
                "✅" if r.correct else "❌",
                f"{r.confidence:.2f}" if r.confidence >= 0 else "N/A",
                r.evidence_source or "N/A",
                r.priority_fix,
                r.analysis_latency_ms, r.coaching_latency_ms, r.total_latency_ms,
                "", "", "", "", r.error,
            ])
    print(f"  → {path}")


def write_feedback_md(results: list[Result]):
    path = RESULTS_DIR / "feedback_for_rating.md"
    lines = [
        "# Coaching Feedback — Pipeline Comparison Rating Sheet\n\n",
        "**Instructions:** Rate each parameter 1–5. Do not look at Option labels until after rating.\n\n",
        "**Question:** Which option produces coaching that most clearly tells you what to fix?\n\n",
        "| Score | Criteria |\n|---|---|\n",
        "| 5 | Specific, accurate, immediately actionable — cites rep counts and trends |\n",
        "| 4 | Accurate but slightly generic — correct issue, vague cue |\n",
        "| 3 | Partially correct — real issue but key fault or trend missed |\n",
        "| 2 | Inaccurate or irrelevant |\n",
        "| 1 | Missing or empty when fault was clearly present |\n\n---\n\n",
    ]

    by_video: dict[str, list[Result]] = {}
    for r in results:
        by_video.setdefault(r.video_id, []).append(r)

    entry_num = 1
    for vid_id, vid_results in by_video.items():
        for r in vid_results:
            if r.error:
                continue
            lines.append(f"## Entry {entry_num} &nbsp;&nbsp; `{vid_id}` &nbsp;·&nbsp; Fault: `{r.fault_key}`\n")
            lines.append(f"<!-- Option: {r.option} | Analysis: {r.analysis_model} → Coaching: {r.coaching_model} -->\n\n")
            if r.verdict:
                lines.append(f"**Verdict:** {r.verdict}\n\n")
            if r.next_session_focus:
                lines.append(f"**Next session focus:** {r.next_session_focus}\n\n")
            for label, fb in [
                ("Posture",           r.feedback_posture),
                ("Stability",         r.feedback_stability),
                ("Movement Quality",  r.feedback_movement),
                ("Range of Motion",   r.feedback_rom),
            ]:
                issue  = fb.get("issue", {}) or {}
                rec    = fb.get("recommendation", {}) or {}
                lines.append(f"### {label} (Priority {fb.get('priority','?')})\n")
                lines.append(f"**Doing well:** {fb.get('doing_well') or '_Not provided_'}\n\n")
                if issue.get("present"):
                    lines.append(f"**Issue:** {issue.get('severity','').upper()} — {issue.get('reps_affected','')} | trend: {issue.get('trend','')} | linked to: {issue.get('connected_to','—')}\n\n")
                else:
                    lines.append(f"**Issue:** _None identified_\n\n")
                lines.append(f"**Cue:** {rec.get('cue') or '_Not provided_'}\n\n")
                lines.append(f"**Drill:** {rec.get('drill') or '_Not provided_'}\n\n")
                lines.append(f"**Progress check:** {rec.get('progress_check') or '_Not provided_'}\n\n")
                lines.append(f"**Rating (1–5):** &nbsp; ___\n\n")
            lines.append("---\n\n")
            entry_num += 1

    path.write_text("".join(lines))
    print(f"  → {path}")


def write_raw_json(results: list[Result]):
    path = RESULTS_DIR / "raw_outputs.json"
    path.write_text(json.dumps([vars(r) for r in results], indent=2, default=str))
    print(f"  → {path}")


def print_summary(results: list[Result]):
    print("\n" + "=" * 62)
    print("  PIPELINE TEST — RESULTS SUMMARY")
    print("=" * 62)

    for option in ["Option 1", "Option 2", "Option 3"]:
        vr = [r for r in results if r.option == option and not r.error]
        if not vr:
            continue
        correct     = sum(1 for r in vr if r.correct)
        avg_total   = sum(r.total_latency_ms for r in vr) / len(vr)
        avg_analysis = sum(r.analysis_latency_ms for r in vr) / len(vr)
        avg_coaching = sum(r.coaching_latency_ms for r in vr) / len(vr)

        print(f"\n  {option}  ({vr[0].analysis_model} → {vr[0].coaching_model})")
        print(f"    Form accuracy    : {correct}/{len(vr)}")
        print(f"    Analysis latency : {avg_analysis:.0f} ms avg")
        print(f"    Coaching latency : {avg_coaching:.0f} ms avg")
        print(f"    Total latency    : {avg_total:.0f} ms avg")

        wrong = [r for r in vr if not r.correct]
        if wrong:
            print(f"    ⚠️  Flagged:")
            for r in wrong:
                print(f"       {r.video_id} | expected={r.ground_truth} got={r.model_prediction} conf={r.confidence:.2f}")

    print("\n" + "=" * 62)


# ── MAIN ─────────────────────────────────────────────────────────────────────

def run_option1_fresh() -> list[Result]:
    """Option 1: Sonnet end-to-end with updated prompts — fresh run."""
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results = []

    for vid_id in GROUND_TRUTH:
        print(f"  {vid_id} ...", end=" ", flush=True)
        if not JSON_FILES[vid_id].exists():
            print(f"SKIP — JSON not found")
            continue

        mp_json = json.loads(JSON_FILES[vid_id].read_text())
        try:
            frames    = extract_frames(VIDEO_FILES[vid_id])
            composite = build_composite(frames)
            prompt    = build_option1_prompt(mp_json, len(frames))

            start = time.time()
            response = client.messages.create(
                model=COACHING_MODEL,
                max_tokens=2000,
                system=OPTION1_SYSTEM,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg", "data": composite,
                    }},
                    {"type": "text", "text": prompt},
                ]}],
            )
            lat = (time.time() - start) * 1000
            combined_out = extract_json(response.content[0].text)

            r = score(vid_id, "Option 1", COACHING_MODEL, {}, combined_out, lat, 0)
            results.append(r)
            print(f"{'✅' if r.correct else '❌'}  {lat:.0f}ms")

        except Exception as exc:
            print(f"ERROR — {exc}")
            results.append(Result(
                video_id=vid_id, option="Option 1",
                analysis_model=COACHING_MODEL, coaching_model=COACHING_MODEL,
                rep_count=-1, fault_key="", ground_truth=False,
                model_prediction=False, correct=False, confidence=-1,
                evidence="", evidence_source="",
                analysis_latency_ms=0, coaching_latency_ms=0, total_latency_ms=0,
                verdict="", priority_fix="", next_session_focus="",
                analysis_output={},
                feedback_posture={}, feedback_stability={},
                feedback_movement={}, feedback_rom={},
                error=str(exc),
            ))
    return results


def run_pipeline(option: str, analysis_fn, video_files: dict) -> list[Result]:
    results = []
    analysis_model = ANALYSIS_MODEL_GEMINI if option == "Option 2" else ANALYSIS_MODEL_HAIKU

    for vid_id in GROUND_TRUTH:
        print(f"  {vid_id} ...", end=" ", flush=True)

        if not JSON_FILES[vid_id].exists():
            print(f"SKIP — {JSON_FILES[vid_id]} not found")
            continue

        mp_json = json.loads(JSON_FILES[vid_id].read_text())

        try:
            # Step 1: Analysis
            analysis_out, analysis_lat = analysis_fn(mp_json, video_files[vid_id])

            # Step 2: Coaching
            print(f"analysis ✅ {analysis_lat:.0f}ms → coaching...", end=" ", flush=True)
            coaching_out, coaching_lat = coach_sonnet(analysis_out)

            r = score(vid_id, option, analysis_model, analysis_out, coaching_out,
                      analysis_lat, coaching_lat)
            results.append(r)
            print(f"✅ {coaching_lat:.0f}ms | total {r.total_latency_ms:.0f}ms | {'✅' if r.correct else '❌'}")

        except Exception as exc:
            print(f"ERROR — {exc}")
            results.append(Result(
                video_id=vid_id, option=option,
                analysis_model=analysis_model, coaching_model=COACHING_MODEL,
                rep_count=-1, fault_key="", ground_truth=False,
                model_prediction=False, correct=False, confidence=-1,
                evidence="", evidence_source="",
                analysis_latency_ms=0, coaching_latency_ms=0, total_latency_ms=0,
                verdict="", priority_fix="", next_session_focus="",
                analysis_output={},
                feedback_posture={}, feedback_stability={},
                feedback_movement={}, feedback_rom={},
                error=str(exc),
            ))

    return results


def main():
    if not ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY not set.")
    if not GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY not set.")

    all_results = []

    # Option 1 — Sonnet end-to-end, fresh run with updated prompts
    print(f"\n{'─'*50}")
    print(f"  Option 1  (Sonnet end-to-end — fresh run, updated prompts)")
    print(f"{'─'*50}")
    all_results.extend(run_option1_fresh())

    # Option 2 — Gemini → Sonnet
    print(f"\n{'─'*50}")
    print(f"  Option 2  (Gemini Flash → Sonnet)")
    print(f"{'─'*50}")
    all_results.extend(run_pipeline("Option 2", analyse_gemini, PROCESSED_VIDEO_FILES))

    # Option 3 — Haiku → Sonnet
    print(f"\n{'─'*50}")
    print(f"  Option 3  (Haiku → Sonnet)")
    print(f"{'─'*50}")
    all_results.extend(run_pipeline("Option 3", analyse_haiku, VIDEO_FILES))

    print("\nWriting outputs...")
    write_scores_csv(all_results)
    write_feedback_md(all_results)
    write_raw_json(all_results)

    print_summary(all_results)
    print(
        "\nNext steps:\n"
        "  1. Check pipeline_results/scores.csv for accuracy comparison\n"
        "  2. Rate coaching quality in pipeline_results/feedback_for_rating.md\n"
        "  3. Compare total latency — Option 2 and 3 have two API calls per video\n"
    )


if __name__ == "__main__":
    main()
