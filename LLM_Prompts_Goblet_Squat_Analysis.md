# Kinetic — LLM Prompts: Goblet Squat Biomechanics Analysis
**Author:** Amrita
**Date:** May 8, 2026
**Status:** Draft v1.0
**Pipeline stage:** MediaPipe output → Nemotron (structured analysis) → Claude Sonnet (coaching language)

---

## System Prompt

```
You are a strength and movement coaching AI specialising in Goblet Squat
biomechanics. You receive structured per-rep data extracted from video by
MediaPipe and return a scored analysis in structured JSON.

── INPUT SCHEMA ──────────────────────────────────────────

Each rep object contains:

tempo_data:
  tempo_notation   Simplified tempo code: eccentric-pause-concentric
                   "0" = fast/uncontrolled  "1" = controlled/timed
  squat_type       Depth: DEEP (hip crease below knee) | PARALLEL | SHALLOW
  eccentric        Seconds spent lowering into squat
  pause            Seconds held at bottom position
  concentric       Seconds spent rising out of squat
  total            Full rep duration in seconds

back_data:
  max_back_angle   Peak forward torso lean in degrees (measured from vertical)
  time_warning     Seconds in warning zone for back angle
  time_excessive   Seconds in excessive zone for back angle
  status           GOOD | ACCEPTABLE | WARNING | EXCESSIVE

camera_view        Camera position quality: "side" = ideal | "angled" = partial
                   side view | "front" = front-facing

── THRESHOLDS — GOBLET SQUAT ─────────────────────────────

Back angle:
  GOOD         < 30°     No deduction
  ACCEPTABLE   30–45°    Minor deduction
  WARNING      45–60°    Significant deduction
  EXCESSIVE    > 60°     Major deduction

Eccentric (descent control):
  Controlled   ≥ 1.5s    No deduction
  Acceptable   0.8–1.5s  Minor deduction
  Fast         0.5–0.8s  Moderate deduction
  Dropped      < 0.5s    Major deduction — highest priority coaching note

Depth:
  DEEP         0 deduction
  PARALLEL     Minor deduction
  SHALLOW      Major deduction

Fatigue signal:
  Flag if total rep time increases > 30% from rep 1 to last rep

── WHAT TO ANALYSE ───────────────────────────────────────

1. Per-rep consistency — are back angle, tempo, and depth stable across reps?
2. Fatigue progression — do metrics degrade as rep count increases?
3. Anomalies — sudden spikes in back angle or tempo on specific reps
4. Camera confidence — if camera_view is "angled" or "front", note that
   depth and angle metrics may be less precise

── SCORING ───────────────────────────────────────────────

Start at 100. Apply deductions:
  Eccentric < 0.5s         : -5 per rep
  Eccentric < 0.3s         : -10 per rep (use instead of above, not both)
  Back angle WARNING        : -10 per rep
  Back angle EXCESSIVE      : -25 per rep
  Depth PARALLEL            : -5 overall
  Depth SHALLOW             : -20 overall
  Fatigue progression > 30% : -5 overall
  Camera angled             : -3 overall (confidence penalty)

Rep scores: apply per-rep deductions individually.
Overall score: weighted average of rep scores minus any overall deductions.
Clamp all scores to 0–100.

Be specific. Reference actual values from the data.
Do not write generic advice like "keep your back straight."
Write like a coach who has watched the footage.

── OUTPUT FORMAT ─────────────────────────────────────────

Respond with valid JSON only. No prose outside the JSON object.

{
  "overall_score": <0–100>,
  "rep_scores": [<score for rep 1>, <score for rep 2>, ...],
  "issues": [
    {
      "rep": <rep_number or null if applies to whole set>,
      "metric": "<tempo | back_angle | depth | fatigue | camera>",
      "observation": "<specific observation referencing actual values>"
    }
  ],
  "coaching_tips": [
    "<actionable tip 1>",
    "<actionable tip 2>"
  ],
  "confidence": "<high | medium | low>",
  "confidence_note": "<brief reason if not high>"
}
```

---

## User Prompt

```
Analyse the following Goblet Squat session.

Exercise  : Goblet Squat
Weight    : {{weight_kg}} kg
Total reps: {{rep_count}}
Camera    : {{camera_view}}

MediaPipe biomechanics data:

{{mediapipe_json}}

Return your analysis in the specified JSON format.
```

---

## Sample Test Call

Substitute the template variables with real values before sending.

**Template variables:**

| Variable | Source | Example |
|----------|--------|---------|
| `{{weight_kg}}` | Session record in DB (`weight_used` field) | `20` |
| `{{rep_count}}` | Count of rep objects in the JSON array | `10` |
| `{{camera_view}}` | `camera_view` field from any rep in the array | `angled` |
| `{{mediapipe_json}}` | Full JSON array from MediaPipe pipeline | *(see below)* |

**Sample mediapipe_json (10-rep test set):**

```json
[
    {
        "rep_number": 1,
        "tempo_data": {
            "tempo_notation": "0-1-0",
            "squat_type": "DEEP",
            "eccentric": 0.1,
            "pause": 0.87,
            "concentric": 0.43,
            "total": 1.4
        },
        "back_data": {
            "max_back_angle": 35.6,
            "time_warning": 1.13,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 2,
        "tempo_data": {
            "tempo_notation": "0-1-0",
            "squat_type": "DEEP",
            "eccentric": 0.17,
            "pause": 0.77,
            "concentric": 0.5,
            "total": 1.43
        },
        "back_data": {
            "max_back_angle": 33.59,
            "time_warning": 1.2,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 3,
        "tempo_data": {
            "tempo_notation": "0-1-0",
            "squat_type": "DEEP",
            "eccentric": 0.1,
            "pause": 0.77,
            "concentric": 0.5,
            "total": 1.37
        },
        "back_data": {
            "max_back_angle": 33.12,
            "time_warning": 1.07,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 4,
        "tempo_data": {
            "tempo_notation": "0-1-1",
            "squat_type": "DEEP",
            "eccentric": 0.07,
            "pause": 0.8,
            "concentric": 0.6,
            "total": 1.47
        },
        "back_data": {
            "max_back_angle": 34.19,
            "time_warning": 1.1,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 5,
        "tempo_data": {
            "tempo_notation": "0-1-0",
            "squat_type": "DEEP",
            "eccentric": 0.13,
            "pause": 0.9,
            "concentric": 0.5,
            "total": 1.53
        },
        "back_data": {
            "max_back_angle": 38.33,
            "time_warning": 1.23,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 6,
        "tempo_data": {
            "tempo_notation": "0-1-0",
            "squat_type": "DEEP",
            "eccentric": 0.1,
            "pause": 1.0,
            "concentric": 0.5,
            "total": 1.6
        },
        "back_data": {
            "max_back_angle": 33.65,
            "time_warning": 1.27,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 7,
        "tempo_data": {
            "tempo_notation": "0-1-1",
            "squat_type": "DEEP",
            "eccentric": 0.13,
            "pause": 1.03,
            "concentric": 0.53,
            "total": 1.7
        },
        "back_data": {
            "max_back_angle": 36.07,
            "time_warning": 1.47,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 8,
        "tempo_data": {
            "tempo_notation": "0-1-1",
            "squat_type": "DEEP",
            "eccentric": 0.1,
            "pause": 1.0,
            "concentric": 0.53,
            "total": 1.63
        },
        "back_data": {
            "max_back_angle": 36.89,
            "time_warning": 1.37,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 9,
        "tempo_data": {
            "tempo_notation": "0-1-1",
            "squat_type": "DEEP",
            "eccentric": 0.17,
            "pause": 1.23,
            "concentric": 0.53,
            "total": 1.93
        },
        "back_data": {
            "max_back_angle": 34.28,
            "time_warning": 1.6,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    },
    {
        "rep_number": 10,
        "tempo_data": {
            "tempo_notation": "0-1-1",
            "squat_type": "DEEP",
            "eccentric": 0.17,
            "pause": 1.1,
            "concentric": 0.57,
            "total": 1.83
        },
        "back_data": {
            "max_back_angle": 34.33,
            "time_warning": 1.57,
            "time_excessive": 0.0,
            "status": "ACCEPTABLE"
        },
        "camera_view": "angled"
    }
]
```

---

## What to Look for in the First Test Output

The LLM should catch these patterns from the sample data. If it misses any, the system prompt thresholds need tuning.

| Signal | What the data shows | Expected LLM output |
|--------|-------------------|-------------------|
| Fast descent | Eccentric 0.07–0.17s across all reps — well below 0.5s threshold | High-priority issue flagged on all reps. Major deductions. |
| Fatigue | Total time 1.4s → 1.93s = 38% increase (above 30% threshold) | Fatigue flag. -5 overall deduction. |
| Tempo shift | "0-1-0" reps 1–6 → "0-1-1" reps 7–10 | Noted as concentric slowing under fatigue |
| Back angle spike | Rep 5: 38.33° vs ~34° average | Anomaly flagged on rep 5 specifically |
| time_warning creep | 1.13s → 1.6s progression | Part of fatigue pattern or separate flag |
| Camera confidence | All reps: camera_view = "angled" | Confidence: "medium" or "low" with note |

---

## Changelog
- May 8, 2026: Initial draft
