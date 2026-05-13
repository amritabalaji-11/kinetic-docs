#!/usr/bin/env python3
"""
Squat Analysis A/B Test Harness
Kinetic AIPM-1

Runs three variants against 6 ground-truth labelled squat videos:
  Control   — MediaPipe JSON only          → meta/llama-3.1-70b-instruct (NVIDIA NIM)
  Variant A — JSON + 32 sampled frames     → nvidia/llama-3.2-90b-vision-instruct (NVIDIA NIM)
  Variant B — JSON + full video            → gemini-2.0-flash (Google AI)

Outputs:
  results/scores.csv              ← form accuracy + latency auto-filled; coaching quality blank for human rating
  results/feedback_for_rating.md  ← coaching feedback anonymised for blind human rating
  results/raw_outputs.json        ← full model responses for debugging

Usage:
  pip install openai google-generativeai opencv-python
  export NVIDIA_API_KEY=your_key
  export GOOGLE_API_KEY=your_key
  python run_test.py
"""

import os
import re
import json
import time
import base64
import csv
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
import google.generativeai as genai
import cv2


# ─── CONFIG ──────────────────────────────────────────────────────────────────

NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

CONTROL_MODEL   = "meta/llama-3.1-70b-instruct"
VARIANT_A_MODEL = "nvidia/llama-3.2-90b-vision-instruct"
VARIANT_B_MODEL = "gemini-2.0-flash"

FRAMES_PER_VIDEO = 32  # ~8 frames per rep for a 4-rep video (Variant A)

VIDEOS_DIR  = Path("videos")   # your 6 .mp4 files
JSON_DIR    = Path("json")     # MediaPipe JSON per video
RESULTS_DIR = Path("results")
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
    return f"""{visual_context}

## Movement Context
This is a GOBLET SQUAT. The athlete holds a weight at chest height.
- Torso should be upright; slight forward lean is acceptable but no slouching
- Excessive lean signals a mobility or technique issue, not normal style variation
- Hip crease at or below knee level defines sufficient depth for this movement

## Important: MediaPipe angle convention
Joint angles in this JSON use MediaPipe's interior-angle convention,
which is the INVERSE of the flexion angle used in biomechanics research papers.

MediaPipe measures the angle between body segments at each joint:
  - Fully extended knee (standing upright) ≈ 180°
  - Knee at parallel (hip crease at knee level) ≈ 90°
  - Deep squat below parallel ≈ 60–70°  (angle DECREASES as you flex deeper)

Do not interpret these as flexion angles from research literature.
When evaluating depth: a LOWER knee_angle_at_bottom = a DEEPER squat.
When evaluating torso lean: a LOWER trunk_angle = more upright posture.

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

**Range of Motion** — Is the full range achieved consistently across all reps?
Look for: hip crease at or below knee, sufficient ankle dorsiflexion (no heel rise), depth consistent not just on rep 1.
Signals available: knee angle at bottom per rep, hip angle at bottom, dorsiflexion angle, rep-to-rep depth variance.

## Rules
- critical_observations must be null (not empty string) when no issue is present
- recommendation must be one specific actionable cue, not generic advice
- evidence must state the exact data point or visual observation behind each fault call

## Output — respond with this exact JSON structure:
{{
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
    "insufficient_depth": "<data point or visual observation>",
    "knee_valgus": "<data point or visual observation>",
    "excessive_forward_lean": "<data point or visual observation>"
  }},
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
    # strip ```json ... ``` or ``` ... ```
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
    rather than uniform intervals. This gives the model more signal-dense frames.
    See extract_key_frames() stub below.
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
    # Fallback to uniform sampling until implemented
    print("    [key-frame extraction not yet implemented — using uniform sampling]")
    return extract_frames_uniform(video_path, n=frames_per_rep)


# ─── VARIANT RUNNERS ─────────────────────────────────────────────────────────

def run_control(mediapipe_json: dict, _video_path: Path) -> tuple[dict, float]:
    """JSON only → llama-3.1-70b via NVIDIA NIM."""
    client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
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
    """JSON + image frames → llama-3.2-90b-vision via NVIDIA NIM."""
    client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
    frames = extract_frames_uniform(video_path)
    prompt = build_prompt(
        mediapipe_json,
        visual_context=f"Attached: {len(frames)} sampled frames from the squat video."
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


def run_variant_b(mediapipe_json: dict, video_path: Path) -> tuple[dict, float]:
    """JSON + full video → Gemini 2.0 Flash."""
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(VARIANT_B_MODEL)

    print("    uploading to Gemini Files API...", end=" ", flush=True)
    video_file = genai.upload_file(path=str(video_path))
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    print("ready")

    prompt = build_prompt(
        mediapipe_json,
        visual_context="Attached: full squat video."
    )
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
    latency_ms:            float
    feedback_posture:      dict
    feedback_stability:    dict
    feedback_movement:     dict
    feedback_rom:          dict
    error:                 str = ""


def score(video_id: str, variant: str, model: str,
          output: dict, latency_ms: float) -> Result:
    gt = GROUND_TRUTH[video_id]
    fault_key = next(k for k, v in gt.items() if v is not None)
    gt_val    = gt[fault_key]
    predicted = output.get("faults_detected", {}).get(fault_key)

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
        evidence         = output.get("evidence",   {}).get(fault_key, ""),
        latency_ms       = round(latency_ms, 1),
        feedback_posture = output.get("feedback", {}).get("posture",          {}),
        feedback_stability = output.get("feedback", {}).get("stability",      {}),
        feedback_movement  = output.get("feedback", {}).get("movement_quality",{}),
        feedback_rom       = output.get("feedback", {}).get("range_of_motion", {}),
    )


# ─── REPORTING ───────────────────────────────────────────────────────────────

def write_scores_csv(results: list[Result]):
    path = RESULTS_DIR / "scores.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "Video", "Variant", "Model", "Fault Tested",
            "Ground Truth", "Model Output", "Correct",
            "Confidence", "Latency (ms)",
            "Posture /5", "Stability /5", "Movement Quality /5",
            "Range of Motion /5", "Notes",
        ])
        for r in results:
            w.writerow([
                r.video_id, r.variant, r.model, r.fault_key,
                r.ground_truth, r.model_prediction,
                "✅" if r.correct else "❌",
                f"{r.confidence:.2f}" if r.confidence >= 0 else "N/A",
                r.latency_ms,
                "", "", "", "", r.error,  # coaching quality left blank for human rating
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

    # shuffle order so variant pattern isn't obvious (group by video, not variant)
    by_video: dict[str, list[Result]] = {}
    for r in results:
        by_video.setdefault(r.video_id, []).append(r)

    entry_num = 1
    for vid_id, vid_results in by_video.items():
        for r in vid_results:
            lines.append(f"## Entry {entry_num} &nbsp;&nbsp; `{vid_id}` &nbsp;·&nbsp; Fault tested: `{r.fault_key}`\n")
            lines.append(f"<!-- Variant: {r.variant} — do not read until after rating -->\n\n")
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
    variants = [("Control", CONTROL_MODEL), ("Variant A", VARIANT_A_MODEL), ("Variant B", VARIANT_B_MODEL)]
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
                      f"confidence={r.confidence:.2f}")
                if r.evidence:
                    print(f"       Evidence: \"{r.evidence}\"")

    print("\n" + "=" * 62)


# ─── RUNNER ──────────────────────────────────────────────────────────────────

VARIANTS = [
    ("Control",   CONTROL_MODEL,   run_control),
    ("Variant A", VARIANT_A_MODEL, run_variant_a),
    ("Variant B", VARIANT_B_MODEL, run_variant_b),
]


def run_all() -> list[Result]:
    results: list[Result] = []

    for variant_name, model_name, runner_fn in VARIANTS:
        print(f"\n{'─'*50}")
        print(f"  {variant_name}  ({model_name})")
        print(f"{'─'*50}")

        for vid_id in GROUND_TRUTH:
            print(f"  {vid_id} ...", end=" ", flush=True)

            if not JSON_FILES[vid_id].exists():
                print(f"SKIP — {JSON_FILES[vid_id]} not found")
                continue

            mp_json = json.loads(JSON_FILES[vid_id].read_text())

            try:
                output, latency_ms = runner_fn(mp_json, VIDEO_FILES[vid_id])
                r = score(vid_id, variant_name, model_name, output, latency_ms)
                results.append(r)
                print(f"{'✅' if r.correct else '❌'}  {latency_ms:.0f} ms")

            except Exception as exc:
                print(f"ERROR — {exc}")
                results.append(Result(
                    video_id=vid_id, variant=variant_name, model=model_name,
                    rep_count=-1, fault_key="", ground_truth=False,
                    model_prediction=False, correct=False, confidence=-1,
                    evidence="", latency_ms=0,
                    feedback_posture={}, feedback_stability={},
                    feedback_movement={}, feedback_rom={},
                    error=str(exc),
                ))

    return results


def main():
    if not NVIDIA_API_KEY:
        raise SystemExit("NVIDIA_API_KEY environment variable not set.")
    if not GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY environment variable not set.")

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
    )


if __name__ == "__main__":
    main()
