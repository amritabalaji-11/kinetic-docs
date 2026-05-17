#!/usr/bin/env python3
"""
Squat Analysis A/B Test Harness
Kinetic AIPM-1

Runs five variants against 6 ground-truth labelled squat videos:
  Control   — MediaPipe JSON only                         → meta/llama-3.1-70b-instruct (NVIDIA NIM)
  Variant A — JSON + 32 sampled frames (original video)   → nvidia/llama-3.2-90b-vision-instruct (NVIDIA NIM)
  Variant B — JSON + full original video                  → gemini-2.0-flash (Google AI)
  Variant D — JSON + processed video (skeleton overlay)   → gemini-2.0-flash (Google AI)
  Variant E — JSON + 32 sampled frames (processed video)  → nvidia/llama-3.2-90b-vision-instruct (NVIDIA NIM)

Outputs:
  results/scores.csv              ← form accuracy + latency auto-filled; coaching quality blank for human rating
  results/feedback_for_rating.md  ← coaching feedback anonymised for blind human rating
  results/raw_outputs.json        ← full model responses for debugging

Usage:
  pip install openai google-generativeai opencv-python
  export NVIDIA_API_KEY_70B=your_70b_key
  export NVIDIA_API_KEY_90B=your_90b_key
  export GOOGLE_API_KEY=your_key
  python run_test.py
"""

import os
import re
import json
import time
import base64
import csv
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI
import google.generativeai as genai
import cv2


# ─── CONFIG ──────────────────────────────────────────────────────────────────

# Falls back to NVIDIA_API_KEY if separate keys are not set
NVIDIA_API_KEY_70B = os.getenv("NVIDIA_API_KEY_70B") or os.getenv("NVIDIA_API_KEY")
NVIDIA_API_KEY_90B = os.getenv("NVIDIA_API_KEY_90B") or os.getenv("NVIDIA_API_KEY")
GOOGLE_API_KEY     = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
NVIDIA_BASE_URL    = "https://integrate.api.nvidia.com/v1"

CONTROL_MODEL   = "meta/llama-3.1-70b-instruct"
VARIANT_A_MODEL = "meta/llama-3.2-90b-vision-instruct"
VARIANT_B_MODEL = "gemini-2.5-flash"
VARIANT_D_MODEL = "gemini-2.5-flash"
VARIANT_E_MODEL = "meta/llama-3.2-90b-vision-instruct"
VARIANT_F_MODEL = "gpt-4o-mini"
VARIANT_G_MODEL = "gpt-4o-mini"
VARIANT_H_MODEL = "claude-haiku-4-5-20251001"
VARIANT_I_MODEL = "claude-haiku-4-5-20251001"
VARIANT_J_MODEL = "claude-sonnet-4-6"

FRAMES_PER_VIDEO = 8  # reduced from 32 — NVIDIA NIM 25MB payload limit

VIDEOS_DIR           = Path("videos")            # 6 original .mp4 files
PROCESSED_VIDEOS_DIR = Path("processed_videos")  # 6 MediaPipe-processed .mp4 files (10fps, skeleton overlay)
JSON_DIR             = Path("json")              # MediaPipe JSON per video
RESULTS_DIR          = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


# ─── GROUND TRUTH ────────────────────────────────────────────────────────────
# None = this fault is not being tested for this video (camera angle cannot capture it)

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


# ─── PROMPT ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a biomechanics analyst evaluating squat form for a fitness coaching "
    "application. Analyze the provided data and return structured feedback. "
    "Respond ONLY in valid JSON. No prose or markdown outside the JSON object."
)

def build_prompt(mediapipe_json: dict, visual_context: str = "") -> str:
    has_visual = bool(visual_context) and "No visual" not in visual_context

    source_rule = (
        "- For each fault in evidence, set source to \"json\", \"visual\", \"both\", or "
        "\"contradictory\" to indicate which input drove the call. If JSON and visual "
        "contradicted each other, set source to \"contradictory\" and add an entry to "
        "source_conflicts explaining what each said, which you trusted, and why. "
        "Set source_conflicts to [] when there are no contradictions.\n"
        if has_visual else ""
    )

    evidence_schema = (
        """    "insufficient_depth":    {"source": "<json|visual|both|contradictory>", "observation": "<data point>"},
    "knee_valgus":           {"source": "<json|visual|both|contradictory>", "observation": "<data point>"},
    "excessive_forward_lean":{"source": "<json|visual|both|contradictory>", "observation": "<data point>"}"""
        if has_visual else
        """    "insufficient_depth":    {"source": "json", "observation": "<data point>"},
    "knee_valgus":           {"source": "json", "observation": "<data point>"},
    "excessive_forward_lean":{"source": "json", "observation": "<data point>"}"""
    )

    return f"""{visual_context}

## Movement Context
This is a GOBLET SQUAT. The athlete holds a weight at chest height.
- Torso should be upright; slight forward lean is acceptable but no slouching
- Excessive lean signals a mobility or technique issue, not normal style variation
- Hip crease at or below knee level defines sufficient depth for this movement

## Angle Convention — When the Inversion Applies

MediaPipe uses interior angles for joint flexion measurements only.
The inversion rule (MediaPipe = 180° − flexion) applies to:

  knee_angle  — lower value = deeper squat (more flexion)
  hip_angle   — lower value = more hip flexion

For all other angle types in this JSON, no conversion is needed —
both MediaPipe and research literature measure from the same reference:

  back_angle / torso_lean  — degrees from vertical   → compare directly
  shin_angle               — degrees from vertical   → compare directly
  hip_drop                 — degrees from horizontal → compare directly
  knee_hip_ratio / valgus  — frontal plane ratio     → compare directly
  foot_angle               — ground plane angle      → compare directly

When comparing a visual angle estimate to the JSON:
- If the angle is knee_angle or hip_angle, convert your estimate first:
  MediaPipe equivalent = 180° − your flexion estimate.
  If the converted value is within ±10° of the JSON value, it is NOT
  a contradiction — it is the same observation in different conventions.
- For all other angles, compare directly. A mismatch is a real conflict.

## Biomechanics JSON
{json.dumps(mediapipe_json, indent=2)}

## Analysis Parameters

**Posture** — Is the spine and torso in the correct position?
Look for: neutral spine, chest tall, slight forward lean acceptable but no slouching, hips square.
Signals available: back angle at bottom (degrees), torso lean degrees, hip alignment symmetry.

**Stability** — Is the base solid and controlled throughout?
Look for: knees tracking over toes (no valgus), feet grounded (no heel lift), no lateral wobble.
Signals available: knee angle deviation, foot presence score, lateral hip sway.

**Movement Quality** — Is the movement fluid, coordinated, and consistent?
Look for: controlled descent, smooth transition at bottom, no lurching, consistency across reps.
Signals available: rep-to-rep angle consistency, descent smoothness, inter-rep variance.
Note: exclude any walk-in/walk-out rep (first or last rep with duration ≥ 3× median) from all timing and consistency assessments here.

**Range of Motion** — Is the full range achieved consistently across all reps?
Look for: hip crease at or below knee, sufficient ankle dorsiflexion (no heel rise), depth consistent not just on rep 1.
Signals available: knee angle at bottom per rep, hip angle at bottom, dorsiflexion angle, rep-to-rep depth variance.

## Rules
- critical_observations must be null (not empty string) when no issue is present
- recommendation must be one specific actionable cue, not generic advice
- evidence must state the exact data point or visual observation behind each fault call
- If the first or last rep has a duration 3× or more than the median rep duration,
  treat it as a walk-in/walk-out rep. Include it in rep_count but exclude it entirely
  from all feedback — posture, stability, movement quality, and range of motion.
  Base all feedback only on the remaining reps.
- For knee valgus detection, use consolidated.stability.session_valgus_fault —
  the authoritative session-level boolean computed by the pipeline (≥50% of valid
  reps have knee_valgus_distance < 0.22). Do NOT use the per-rep valgus_flag.
{source_rule}- verdict must always be present: 2–3 sentences, second person, action-oriented.
  Focus on what the user should do or fix, not what you observed. If fixing one issue
  will biomechanically affect another parameter, call that out explicitly. If no faults,
  summarise the top 1–2 things to maintain in the next session.

## Output — respond with this exact JSON structure:
{{
  "verdict": "<2–3 sentences. Action-oriented, second person. What to fix or maintain. Call out cross-parameter biomechanical links if relevant.>",
  "rep_count": <integer>,
  "faults_detected": {{
    "insufficient_depth": <true|false>,
    "knee_valgus": <true|false>,
    "excessive_forward_lean": <true|false>
  }},
  "confidence": {{
    "insufficient_depth": <0.0-1.0>,
    "knee_valgus": <0.0-1.0>,
    "excessive_forward_lean": <0.0-1.0>
  }},
  "evidence": {{
{evidence_schema}
  }},
  "source_conflicts": [],
  "feedback": {{
    "posture": {{
      "doing_well": "<1-2 sentences>",
      "critical_observations": "<1-2 sentences or null>",
      "recommendation": "<one specific actionable cue>"
    }},
    "stability": {{
      "doing_well": "<1-2 sentences>",
      "critical_observations": "<1-2 sentences or null>",
      "recommendation": "<one specific actionable cue>"
    }},
    "movement_quality": {{
      "doing_well": "<1-2 sentences>",
      "critical_observations": "<1-2 sentences or null>",
      "recommendation": "<one specific actionable cue>"
    }},
    "range_of_motion": {{
      "doing_well": "<1-2 sentences>",
      "critical_observations": "<1-2 sentences or null>",
      "recommendation": "<one specific actionable cue>"
    }}
  }}
}}"""


# ─── JSON EXTRACTION ─────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict:
    """Parse JSON from model response, stripping markdown fences if present."""
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if fence:
        raw = fence.group(1)
    return json.loads(raw)


# ─── FRAME EXTRACTION ────────────────────────────────────────────────────────

def extract_frames_uniform(video_path: Path, n: int = FRAMES_PER_VIDEO) -> list[str]:
    """
    Sample n evenly-spaced frames from the video.
    Returns list of base64-encoded JPEG strings.

    TODO (optional upgrade): replace with key-moment sampling using MediaPipe
    knee angle peaks — sample frames at top-of-squat and peak-depth positions
    rather than uniform intervals. See extract_key_frames() stub below.
    """
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


def extract_key_frames(knee_angles: list[float], video_path: Path,
                       frames_per_rep: int = 8) -> list[str]:
    """
    TODO: Implement key-moment frame extraction.

    Use MediaPipe knee angle time series to find rep peaks (top) and troughs
    (peak depth), then sample frames_per_rep frames around those moments.

    Args:
        knee_angles:    knee flexion angle per frame from MediaPipe JSON
        video_path:     path to the video file
        frames_per_rep: total frames to return per detected rep

    Returns:
        List of base64-encoded JPEG strings at key moments

    Guidance:
        from scipy.signal import find_peaks
        - Peak depth = minimum knee angle → use find_peaks(-np.array(knee_angles))
        - Set distance param to ~90 frames (3s at 30fps) to avoid detecting noise as reps
        - For each trough, sample symmetrically: frames_per_rep//2 before and after
    """
    print("    [key-frame extraction not yet implemented — using uniform sampling]")
    return extract_frames_uniform(video_path, n=frames_per_rep)


# ─── VARIANT RUNNERS ─────────────────────────────────────────────────────────

def run_control(mediapipe_json: dict, _video_path: Path) -> tuple[dict, float]:
    """JSON only → llama-3.1-70b via NVIDIA NIM."""
    client = OpenAI(api_key=NVIDIA_API_KEY_70B, base_url=NVIDIA_BASE_URL)
    prompt = build_prompt(
        mediapipe_json,
        visual_context="No visual data provided. Analyze the biomechanics JSON only."
    )
    start = time.time()
    response = client.chat.completions.create(
        model=CONTROL_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.choices[0].message.content), latency_ms


def run_variant_a(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + 32 uniform frames (original video) → llama-3.2-90b-vision via NVIDIA NIM."""
    client = OpenAI(api_key=NVIDIA_API_KEY_90B, base_url=NVIDIA_BASE_URL)
    frames = extract_frames_uniform(video_path)
    prompt = build_prompt(
        mediapipe_json,
        visual_context=f"Attached: {len(frames)} frames sampled from the original squat video."
    )
    content: list[dict] = [{"type": "text", "text": prompt}]
    for frame_b64 in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"},
        })
    start = time.time()
    response = client.chat.completions.create(
        model=VARIANT_A_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.choices[0].message.content), latency_ms


def _run_gemini_video(mediapipe_json: dict, video_path: Path,
                      visual_context: str) -> tuple[dict, float]:
    """Shared logic for Gemini video variants (B and D)."""
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(VARIANT_B_MODEL)

    print("    uploading to Gemini Files API...", end=" ", flush=True)
    video_file = genai.upload_file(path=str(video_path))
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    print("ready")

    prompt = build_prompt(mediapipe_json, visual_context=visual_context)
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


def run_variant_b(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + full original video → Gemini 2.0 Flash."""
    return _run_gemini_video(
        mediapipe_json, video_path,
        visual_context="Attached: full original squat video."
    )


def run_variant_d(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + processed video (10fps skeleton overlay) → Gemini 2.0 Flash."""
    return _run_gemini_video(
        mediapipe_json, video_path,
        visual_context=(
            "Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. "
            "Green lines indicate detected joint positions per frame."
        )
    )


def build_composite_frame(frames_b64: list[str], cols: int = 4) -> str:
    """
    Combine multiple base64 JPEG frames into a single composite grid image.
    NVIDIA NIM allows only 1 image per request — this gets around that limit.
    Returns a single base64-encoded JPEG of the grid.
    """
    import math
    frames = []
    for b64 in frames_b64:
        buf = base64.b64decode(b64)
        arr = cv2.imdecode(
            __import__("numpy").frombuffer(buf, dtype=__import__("numpy").uint8),
            cv2.IMREAD_COLOR
        )
        if arr is not None:
            frames.append(arr)

    if not frames:
        return frames_b64[0]

    rows = math.ceil(len(frames) / cols)
    h, w = frames[0].shape[:2]
    thumb_w, thumb_h = min(w, 320), min(h, 240)

    grid_rows = []
    for r in range(rows):
        row_frames = frames[r * cols:(r + 1) * cols]
        # pad row to full cols width
        while len(row_frames) < cols:
            row_frames.append(__import__("numpy").zeros((thumb_h, thumb_w, 3), dtype=__import__("numpy").uint8))
        resized = [cv2.resize(f, (thumb_w, thumb_h)) for f in row_frames]
        grid_rows.append(__import__("numpy").hstack(resized))
    grid = __import__("numpy").vstack(grid_rows)

    _, buf = cv2.imencode(".jpg", grid, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode("utf-8")


def run_variant_e(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (processed video) → llama-3.2-90b-vision via NVIDIA NIM.
    Frames are combined into a single image grid to satisfy the 1-image-per-request limit.
    """
    client = OpenAI(api_key=NVIDIA_API_KEY_90B, base_url=NVIDIA_BASE_URL)
    frames = extract_frames_uniform(video_path)
    composite_b64 = build_composite_frame(frames)
    prompt = build_prompt(
        mediapipe_json,
        visual_context=(
            f"Attached: a composite grid of {len(frames)} frames sampled from the squat video "
            f"processed at 10fps with MediaPipe skeleton overlay. Green lines indicate detected "
            f"joint positions. Frames are arranged left-to-right, top-to-bottom in time order."
        )
    )
    content: list[dict] = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{composite_b64}"}},
    ]
    start = time.time()
    response = client.chat.completions.create(
        model=VARIANT_E_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.choices[0].message.content), latency_ms


def _run_openai_frames(mediapipe_json: dict, video_path: Path,
                       model: str, visual_context_prefix: str) -> tuple[dict, float]:
    """Shared logic for OpenAI vision variants (F and G) — sends composite frame grid."""
    from openai import OpenAI as _OpenAI
    client = _OpenAI(api_key=OPENAI_API_KEY)
    frames = extract_frames_uniform(video_path)
    composite_b64 = build_composite_frame(frames)
    prompt = build_prompt(mediapipe_json, visual_context=(
        f"{visual_context_prefix} Frames are arranged left-to-right, top-to-bottom in time order."
    ))
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{composite_b64}"
                }},
            ]},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.choices[0].message.content), latency_ms


def run_variant_f(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (original video) → GPT-4o mini."""
    return _run_openai_frames(
        mediapipe_json, video_path, VARIANT_F_MODEL,
        f"Attached: a composite grid of {FRAMES_PER_VIDEO} frames sampled from the original squat video."
    )


def run_variant_g(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (processed video, skeleton overlay) → GPT-4o mini."""
    return _run_openai_frames(
        mediapipe_json, video_path, VARIANT_G_MODEL,
        f"Attached: a composite grid of {FRAMES_PER_VIDEO} frames from the squat video processed "
        f"at 10fps with MediaPipe skeleton overlay. Green lines indicate detected joint positions."
    )


def _run_anthropic_frames(mediapipe_json: dict, video_path: Path,
                          model: str, visual_context_prefix: str) -> tuple[dict, float]:
    """Shared logic for Anthropic vision variants (H and I) — sends composite frame grid."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    frames = extract_frames_uniform(video_path)
    composite_b64 = build_composite_frame(frames)
    prompt = build_prompt(mediapipe_json, visual_context=(
        f"{visual_context_prefix} Frames are arranged left-to-right, top-to-bottom in time order."
    ))
    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": composite_b64,
            }},
            {"type": "text", "text": prompt},
        ]}],
    )
    latency_ms = (time.time() - start) * 1000
    return extract_json(response.content[0].text), latency_ms


def run_variant_h(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (original video) → Claude Haiku."""
    return _run_anthropic_frames(
        mediapipe_json, video_path, VARIANT_H_MODEL,
        f"Attached: a composite grid of {FRAMES_PER_VIDEO} frames sampled from the original squat video."
    )


def run_variant_i(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (processed video, skeleton overlay) → Claude Haiku."""
    return _run_anthropic_frames(
        mediapipe_json, video_path, VARIANT_I_MODEL,
        f"Attached: a composite grid of {FRAMES_PER_VIDEO} frames from the squat video processed "
        f"at 10fps with MediaPipe skeleton overlay. Green lines indicate detected joint positions."
    )


def run_variant_j(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + composite frame grid (original video) → Claude Sonnet."""
    return _run_anthropic_frames(
        mediapipe_json, video_path, VARIANT_J_MODEL,
        f"Attached: a composite grid of {FRAMES_PER_VIDEO} frames sampled from the original squat video."
    )


# ─── SCORING ─────────────────────────────────────────────────────────────────

@dataclass
class Result:
    video_id:              str
    variant:               str
    model:                 str
    rep_count:             int
    fault_key:             str
    ground_truth:          bool
    model_prediction:      bool
    correct:               bool
    confidence:            float
    evidence:              str
    evidence_source:       str
    latency_ms:            float
    verdict:               str
    feedback_posture:      dict
    feedback_stability:    dict
    feedback_movement:     dict
    feedback_rom:          dict
    source_conflicts:      list = field(default_factory=list)
    error:                 str  = ""


def score(video_id: str, variant: str, model: str,
          output: dict, latency_ms: float) -> Result:
    gt        = GROUND_TRUTH[video_id]
    fault_key = next(k for k, v in gt.items() if v is not None)
    gt_val    = gt[fault_key]
    predicted = output.get("faults_detected", {}).get(fault_key)

    evidence_raw = output.get("evidence", {}).get(fault_key, {})
    if isinstance(evidence_raw, dict):
        evidence_obs = evidence_raw.get("observation", "")
        evidence_src = evidence_raw.get("source", "")
    else:
        evidence_obs = str(evidence_raw)
        evidence_src = ""

    return Result(
        video_id         = video_id,
        variant          = variant,
        model            = model,
        rep_count        = output.get("rep_count", -1),
        fault_key        = fault_key,
        ground_truth     = gt_val,
        model_prediction = predicted,
        correct          = (predicted == gt_val),
        confidence       = output.get("confidence", {}).get(fault_key, -1.0),
        evidence         = evidence_obs,
        evidence_source  = evidence_src,
        latency_ms       = round(latency_ms, 1),
        verdict          = output.get("verdict", ""),
        source_conflicts = output.get("source_conflicts", []),
        feedback_posture   = output.get("feedback", {}).get("posture",           {}),
        feedback_stability = output.get("feedback", {}).get("stability",         {}),
        feedback_movement  = output.get("feedback", {}).get("movement_quality",  {}),
        feedback_rom       = output.get("feedback", {}).get("range_of_motion",   {}),
    )


# ─── REPORTING ───────────────────────────────────────────────────────────────

def write_scores_csv(results: list[Result]):
    path = RESULTS_DIR / "scores.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Video", "Variant", "Model", "Fault Tested",
            "Ground Truth", "Model Output", "Correct",
            "Confidence", "Evidence Source", "Latency (ms)",
            "Posture /5", "Stability /5", "Movement Quality /5",
            "Range of Motion /5", "Notes",
        ])
        for r in results:
            w.writerow([
                r.video_id, r.variant, r.model, r.fault_key,
                r.ground_truth, r.model_prediction,
                "✅" if r.correct else "❌",
                f"{r.confidence:.2f}" if r.confidence >= 0 else "N/A",
                r.evidence_source or "N/A",
                r.latency_ms,
                "", "", "", "", r.error,
            ])
    print(f"  → {path}")


def write_feedback_md(results: list[Result]):
    """Anonymised coaching feedback for blind human rating."""
    path = RESULTS_DIR / "feedback_for_rating.md"
    lines = [
        "# Coaching Feedback — Blind Rating Sheet\n\n",
        "**Instructions:** Rate each parameter 1–5 using the rubric below.  \n",
        "**Do not look at the Variant column until you have finished rating all entries.**\n\n",
        "| Score | Criteria |\n",
        "|---|---|\n",
        "| 5 | Specific, accurate, immediately actionable cue directly addressing the observed movement |\n",
        "| 4 | Accurate but slightly generic — correct issue, vague cue |\n",
        "| 3 | Partially correct — real issue mentioned but key fault missed |\n",
        "| 2 | Inaccurate or irrelevant — wrong fault identified |\n",
        "| 1 | Missing, empty, or null when fault was clearly present |\n\n",
        "---\n\n",
    ]

    by_video: dict[str, list[Result]] = {}
    for r in results:
        by_video.setdefault(r.video_id, []).append(r)

    entry_num = 1
    for vid_id, vid_results in by_video.items():
        for r in vid_results:
            lines.append(f"## Entry {entry_num} &nbsp;&nbsp; `{vid_id}` &nbsp;·&nbsp; Fault tested: `{r.fault_key}`\n")
            lines.append(f"<!-- Variant: {r.variant} — do not read until after rating -->\n\n")

            if r.verdict:
                lines.append(f"**Verdict:** {r.verdict}\n\n")

            for label, fb in [
                ("Posture",           r.feedback_posture),
                ("Stability",         r.feedback_stability),
                ("Movement Quality",  r.feedback_movement),
                ("Range of Motion",   r.feedback_rom),
            ]:
                lines.append(f"### {label}\n")
                lines.append(f"**Doing well:** {fb.get('doing_well') or '_Not provided_'}\n\n")
                obs = fb.get('critical_observations')
                lines.append(f"**Critical observations:** {obs if obs else '_None identified_'}\n\n")
                lines.append(f"**Recommendation:** {fb.get('recommendation') or '_Not provided_'}\n\n")
                lines.append(f"**Rating (1–5):** &nbsp; ___\n\n")
            lines.append("---\n\n")
            entry_num += 1

    path.write_text("".join(lines))
    print(f"  → {path}")


def write_raw_json(results: list[Result]):
    path = RESULTS_DIR / "raw_outputs.json"
    path.write_text(json.dumps(
        [vars(r) for r in results], indent=2, default=str
    ))
    print(f"  → {path}")


def print_summary(results: list[Result]):
    variants = [
        ("Control",   CONTROL_MODEL),
        ("Variant A", VARIANT_A_MODEL),
        ("Variant B", VARIANT_B_MODEL),
        ("Variant D", VARIANT_D_MODEL),
        ("Variant E", VARIANT_E_MODEL),
        ("Variant F", VARIANT_F_MODEL),
        ("Variant G", VARIANT_G_MODEL),
        ("Variant H", VARIANT_H_MODEL),
        ("Variant I", VARIANT_I_MODEL),
        ("Variant J", VARIANT_J_MODEL),
    ]
    print("\n" + "=" * 62)
    print("  RESULTS SUMMARY")
    print("=" * 62)

    for variant_name, model_name in variants:
        vr = [r for r in results if r.variant == variant_name]
        if not vr:
            continue
        correct     = sum(1 for r in vr if r.correct)
        avg_latency = sum(r.latency_ms for r in vr) / len(vr)
        p95_latency = sorted(r.latency_ms for r in vr)[int(len(vr) * 0.95)]

        print(f"\n  {variant_name}  ({model_name})")
        print(f"    Form accuracy : {correct}/{len(vr)}")
        print(f"    Avg latency   : {avg_latency:.0f} ms")
        print(f"    p95 latency   : {p95_latency:.0f} ms")

        wrong = [r for r in vr if not r.correct]
        if wrong:
            print(f"    ⚠️  Flagged for review:")
            for r in wrong:
                print(f"       {r.video_id} | expected={r.ground_truth} got={r.model_prediction} "
                      f"confidence={r.confidence:.2f} source={r.evidence_source}")
                if r.evidence:
                    print(f"       Evidence: \"{r.evidence}\"")
            conflicts = [r for r in vr if r.source_conflicts]
            if conflicts:
                print(f"    ⚠️  Source conflicts detected in {len(conflicts)} result(s) — see raw_outputs.json")

    print("\n" + "=" * 62)


# ─── RUNNER ──────────────────────────────────────────────────────────────────

VARIANTS = [
    ("Variant J", VARIANT_J_MODEL, run_variant_j, VIDEO_FILES),
]


def run_all() -> list[Result]:
    results: list[Result] = []

    for variant_name, model_name, runner_fn, video_files in VARIANTS:
        print(f"\n{'─'*50}")
        print(f"  {variant_name}  ({model_name})")
        print(f"{'─'*50}")

        # Skip variants D and E if processed videos folder is missing
        if video_files is PROCESSED_VIDEO_FILES and not PROCESSED_VIDEOS_DIR.exists():
            print(f"  SKIP — processed_videos/ folder not found. Run MediaPipe pipeline first.")
            continue

        for vid_id in GROUND_TRUTH:
            print(f"  {vid_id} ...", end=" ", flush=True)

            if not JSON_FILES[vid_id].exists():
                print(f"SKIP — {JSON_FILES[vid_id]} not found")
                continue

            mp_json = json.loads(JSON_FILES[vid_id].read_text())

            try:
                output, latency_ms = runner_fn(mp_json, video_files[vid_id])
                r = score(vid_id, variant_name, model_name, output, latency_ms)
                results.append(r)
                print(f"{'✅' if r.correct else '❌'}  {latency_ms:.0f} ms")

            except Exception as exc:
                print(f"ERROR — {exc}")
                results.append(Result(
                    video_id=vid_id, variant=variant_name, model=model_name,
                    rep_count=-1, fault_key="", ground_truth=False,
                    model_prediction=False, correct=False, confidence=-1,
                    evidence="", evidence_source="", latency_ms=0,
                    verdict="",
                    feedback_posture={}, feedback_stability={},
                    feedback_movement={}, feedback_rom={},
                    error=str(exc),
                ))

    return results


def main():
    needs = {r[1] for r in VARIANTS}
    if any(m in needs for m in [CONTROL_MODEL, VARIANT_A_MODEL, VARIANT_E_MODEL]) and not NVIDIA_API_KEY_70B:
        raise SystemExit("NVIDIA_API_KEY_70B environment variable not set.")
    if any(m in needs for m in [VARIANT_A_MODEL, VARIANT_E_MODEL]) and not NVIDIA_API_KEY_90B:
        raise SystemExit("NVIDIA_API_KEY_90B environment variable not set.")
    if any(m in needs for m in [VARIANT_B_MODEL, VARIANT_D_MODEL]) and not GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY environment variable not set.")
    if any(m in needs for m in [VARIANT_F_MODEL, VARIANT_G_MODEL]) and not OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY environment variable not set.")
    if any(m in needs for m in [VARIANT_H_MODEL, VARIANT_I_MODEL, VARIANT_J_MODEL]) and not ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY environment variable not set.")

    results = run_all()

    print("\nWriting outputs...")
    write_scores_csv(results)
    write_feedback_md(results)
    write_raw_json(results)

    print_summary(results)
    print(
        "\nNext steps:\n"
        "  1. Open results/feedback_for_rating.md — rate coaching quality blind\n"
        "  2. Add your ratings to the Posture/Stability/Movement/RoM columns in results/scores.csv\n"
        "  3. Review flagged entries above — check evidence field in raw_outputs.json\n"
        "  4. Check source_conflicts in raw_outputs.json for any JSON vs visual disagreements\n"
    )


if __name__ == "__main__":
    main()
