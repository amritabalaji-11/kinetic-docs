# A/B Test: Squat Analysis Model Comparison
**Project:** Kinetic AIPM-1  
**Version:** 1.0  
**Status:** Draft  

---

## 1. Objective

Determine whether adding visual input (image frames or full video) to biomechanics JSON improves squat form analysis accuracy, and whether the improvement justifies the added latency and cost.

**Priority order:** Form Accuracy > Latency > Coaching Quality

---

## 2. Hypothesis

| Hypothesis | Expectation |
|---|---|
| H1 | JSON + image frames outperforms JSON-only on knee tracking detection (frontal view captures valgus that angles cannot) |
| H2 | JSON + video outperforms JSON + frames on temporal faults (tempo, consistency across reps) |
| H3 | JSON-only matches or outperforms visual variants on depth and torso (angles are exact; VLM is estimating) |
| H4 | Skeleton-overlay video (Variant D) outperforms raw video (Variant B) for Gemini — pre-drawn joints reduce visual ambiguity |
| H5 | Skeleton-overlay video (Variant E) outperforms sampled raw frames (Variant A) for NVIDIA 90B — full annotated video gives more temporal context than 32 static frames |

---

## 3. Why JSON-Only is the Control

The control variant uses **MediaPipe JSON angles with no visual input**. This is intentional, not a shortcut.

**Reason 1 — Establish the true baseline**  
Before adding visual complexity, you need to know what pure numerical analysis already gets right. Depth (knee angle) and torso lean (trunk inclination) are *exactly* what MediaPipe measures in degrees. If a text LLM reading those numbers matches a VLM watching the video, the visual pipeline adds cost with no benefit.

**Reason 2 — Isolate the variable**  
Without a control, you cannot answer "does visual input help?" — you can only answer "which visual approach is better?" The control anchors the comparison. A result of Control: 4/6, Variant A: 5/6, Variant B: 5/6 tells you visual adds one correct call. Without Control, you cannot see that.

**Reason 3 — Cost and architecture justification**  
Visual inference is 10–50× more expensive per call than text inference. The control result defines the cost/accuracy tradeoff. If Control scores 5/6 and Variant B scores 6/6, you are paying 50× more for one additional correct detection — a business decision, not just a technical one.

**Reason 4 — Expose hallucination**  
VLMs sometimes confidently describe faults they cannot actually see (especially knee valgus from a side-view video). The control cannot hallucinate visual information it was never given. Comparing Control vs Variant scores on the same video reveals whether the VLM is detecting or guessing.

---

## 4. Test Variants

| Variant | Input | Model | API |
|---|---|---|---|
| **Control** | MediaPipe JSON only | `meta/llama-3.1-70b-instruct` | NVIDIA NIM |
| **Variant A** | JSON + 8 frames composite (original video) | `meta/llama-3.2-90b-vision-instruct` | NVIDIA NIM |
| **Variant B** | JSON + full original video | `gemini-2.5-flash` | Google AI API |
| **Variant D** | JSON + full processed video (skeleton overlay) | `gemini-2.5-flash` | Google AI API |
| **Variant E** | JSON + 8 frames composite (processed video) | `meta/llama-3.2-90b-vision-instruct` | NVIDIA NIM |
| **Variant F** | JSON + 8 frames composite (original video) | `gpt-4o-mini` | OpenAI |
| **Variant G** | JSON + 8 frames composite (processed video) | `gpt-4o-mini` | OpenAI |
| **Variant H** | JSON + 8 frames composite (original video) | `claude-haiku-4-5-20251001` | Anthropic |
| **Variant I** | JSON + 8 frames composite (processed video) | `claude-haiku-4-5-20251001` | Anthropic |

**Processed video:** Output of the MediaPipe Full model pipeline — 10fps video with green skeleton lines overlaid on each frame. Already generated as part of the standard pipeline; no extra processing step needed.

**Comparison matrix:**

| | Original video (frames) | Full original video | Processed video (frames) | Full processed video |
|---|---|---|---|---|
| **Llama 3.2 90B** (NVIDIA) | Variant A | — | Variant E | — |
| **Gemini 2.5 Flash** (Google) | — | Variant B | — | Variant D |
| **GPT-4o mini** (OpenAI) | Variant F | — | Variant G | — |
| **Claude Haiku 4.5** (Anthropic) | Variant H | — | Variant I | — |

> **Note on Variant C:** Reserved for Nemotron once model access is confirmed on build.nvidia.com.

---

## 5. Test Set — 6 Videos

Film one fault and one good execution per fault category. Same person, same session per angle group.

| # | Fault Category | Condition | Camera Angle | Height | What to Film |
|---|---|---|---|---|---|
| V1 | Depth | **FAULT** | Side (90°) | Hip level | Quarter squat — stop at ~45° knee bend, deliberate and consistent |
| V2 | Depth | **GOOD** | Side (90°) | Hip level | Hip crease clearly below knee at bottom of each rep |
| V3 | Knee Tracking | **FAULT** | Front (0°) | Knee–hip level | Knees collapsing inward on descent, slight exaggeration |
| V4 | Knee Tracking | **GOOD** | Front (0°) | Knee–hip level | Knees tracking directly over middle toe throughout |
| V5 | Torso | **FAULT** | Side (90°) | Hip level | Trunk nearly parallel to floor at bottom, chest down |
| V6 | Torso | **GOOD** | Side (90°) | Hip level | Chest up, relatively upright throughout movement |

**Filming requirements for all videos:**
- 3–5 reps per video (model needs multiple reps)
- Landscape orientation
- Fitted clothing (no baggy shorts — hides knee landmarks)
- Plain background, avoid backlight
- Camera on tripod or stable surface
- Videos 1, 2, 5, 6 can be filmed in one setup (same side angle); move camera for V3 and V4

**Ground truth labels (fill in after filming):**

| Video | insufficient_depth | knee_valgus | excessive_lean | Confirmed by |
|---|---|---|---|---|
| V1 | TRUE | N/A | N/A | |
| V2 | FALSE | N/A | N/A | |
| V3 | N/A | TRUE | N/A | |
| V4 | N/A | FALSE | N/A | |
| V5 | N/A | N/A | TRUE | |
| V6 | N/A | N/A | FALSE | |

---

## 6. Fault Thresholds

These thresholds are computed by the MediaPipe pipeline and output as flags in each rep's JSON. The test script reads these flags directly — no manual threshold setting needed before running.

| Fault | JSON field | Threshold | Camera view | Notes |
|---|---|---|---|---|
| Insufficient depth | `depth_data.depth_insufficient_flag` | `knee_angle_at_bottom > 97°` | Side (V1, V2) | Lower angle = deeper squat (MediaPipe convention) |
| Excessive lean | `back_data.status` | `back_angle_max > 45°` | Side (V5, V6) | Checked at worst lean point across the rep |
| Knee valgus | `consolidated.stability.session_valgus_fault` | ≥50% of valid reps have `knee_valgus_distance < 0.22` | Front (V3, V4) | Session-level flag computed by pipeline. Per-rep `valgus_flag` retained in JSON but not used for fault detection. |

**If you need to adjust a threshold**, change it in the MediaPipe extraction script — not here. The JSON output will reflect the updated values automatically.

---

## 7. Shared Prompt Template

Use this exact prompt across all three variants. Only the `{visual_input}` line changes per variant.

```
You are a biomechanics analyst evaluating squat form for a fitness coaching 
application. Analyze the provided data and return structured feedback.

## Input
{visual_input}
← Control:   omit this line entirely
← Variant A: "Attached: {N} frames sampled from the original squat video."
← Variant B: "Attached: full original squat video."
← Variant D: "Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. Green lines indicate detected joint positions per frame."
← Variant E: "Attached: full squat video processed at 10fps with MediaPipe skeleton overlay. Green lines indicate detected joint positions per frame."

## Biomechanics JSON
The following joint angle data was extracted by MediaPipe, one entry per frame:
{mediapipe_json}

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

## Movement Context

This is a GOBLET SQUAT. The athlete holds a weight at chest height.
Standards differ from a barbell back squat:
- Torso should be upright; slight forward lean is acceptable but no slouching
- Weight at chest naturally encourages an upright position — excessive lean 
  signals a mobility or technique issue
- Hip crease at or below knee defines sufficient depth for this movement

## Analysis Parameters

Evaluate the squat on these four parameters. For each, provide all three 
components based on what you can observe from the data provided.

**Posture**
Is the spine and torso in the correct position throughout the movement?
Look for: neutral spine, chest tall, slight forward lean acceptable but 
no slouching or rounding, hips square throughout.
Biomechanics signals available: back angle at bottom (degrees), torso lean 
degrees, hip alignment symmetry.

**Stability**
Is the base solid and controlled throughout the movement?
Look for: knees tracking over toes (no valgus collapse), feet grounded 
with no heel lift, no lateral wobble or hip sway between reps.
Biomechanics signals available: knee angle deviation from ideal tracking 
line, foot presence score, lateral hip sway measurements.

**Movement Quality**
Is the movement fluid, coordinated, and consistent?
Look for: controlled descent with no lurching or collapsing, smooth 
transition at the bottom, no sudden acceleration, consistency across reps.
Biomechanics signals available: rep-to-rep angle consistency, descent 
smoothness curve, inter-rep variance.
Note: if the first or last rep has duration ≥ 3× the median, exclude it 
entirely from all feedback here and in all other parameters.

**Range of Motion**
Is the full range being achieved consistently across all reps?
Look for: hip crease at or below knee level at the bottom, sufficient 
ankle dorsiflexion (no heel rise compensating for ankle mobility), 
depth maintained consistently — not just on the first rep.
Biomechanics signals available: knee angle at bottom per rep, hip angle 
at bottom per rep, dorsiflexion angle, descent time per rep, 
rep-to-rep depth variance.

## Rules
- Respond ONLY in the JSON format below. No prose outside the JSON.
- If a parameter cannot be assessed from available data, set the relevant 
  field to null and explain why in critical_observations.
- critical_observations must be null — not an empty string — when no 
  issue is present.
- recommendation must be one specific, actionable cue (not generic advice).
- evidence must state exactly what data point led to each fault detection.
- verdict must always be present. Write 2–3 sentences in second person, 
  action-oriented (what the user should do or focus on — not what you 
  observed). If fixing one issue will biomechanically affect another, call 
  that out explicitly. If there are no faults, summarise the top 1–2 things 
  the user should keep doing to maintain form in their next session.
- For all variants with visual input (video or frames): set evidence.source 
  to "json", "visual", or "both" to indicate which input drove the fault 
  call. If JSON and visual contradicted each other, set source to 
  "contradictory" and add an entry to source_conflicts explaining what each 
  said, which you trusted, and why. source_conflicts should be an empty 
  array [] when there are no contradictions.
- If the first or last rep has a duration 3× or more than the median rep 
  duration, treat it as a walk-in/walk-out rep (user moving to or from the 
  camera). Include it in rep_count but do not use it as the basis for any 
  feedback — exclude it entirely from posture, stability, movement quality, 
  and range of motion assessments. Base all feedback only on the remaining 
  reps.
- For knee valgus detection, use `consolidated.stability.session_valgus_fault`
  — this is the authoritative session-level boolean, computed by the pipeline
  as: ≥50% of valid reps (excl. walk-in/out) have knee_valgus_distance < 0.22.
  Do NOT use the per-rep `valgus_flag` boolean — it is too sensitive for
  session-level fault detection.

## Output Format

{
  "verdict": "<2–3 sentences. Action-oriented, second person. What to focus on or fix. If fixing one issue will affect another parameter, name the connection. If no faults, state what to keep doing next session.>",
  "rep_count": <integer>,
  "faults_detected": {
    "insufficient_depth": <true|false>,
    "knee_valgus": <true|false>,
    "excessive_forward_lean": <true|false>
  },
  "confidence": {
    "insufficient_depth": <0.0–1.0>,
    "knee_valgus": <0.0–1.0>,
    "excessive_forward_lean": <0.0–1.0>
  },
  "evidence": {
    "insufficient_depth": {
      "source": "<json|visual|both|contradictory>",
      "observation": "<exact data point or visual observation>"
    },
    "knee_valgus": {
      "source": "<json|visual|both|contradictory>",
      "observation": "<exact data point or visual observation>"
    },
    "excessive_forward_lean": {
      "source": "<json|visual|both|contradictory>",
      "observation": "<exact data point or visual observation>"
    }
  },
  "source_conflicts": [
    {
      "fault": "<insufficient_depth|knee_valgus|excessive_forward_lean>",
      "json_says": "<what the JSON data indicated>",
      "visual_says": "<what the video/frames indicated>",
      "decided": "<json|visual>",
      "reason": "<why you trusted one over the other>"
    }
  ],
  "feedback": {
    "posture": {
      "doing_well": "<1–2 sentences on what the user is doing correctly>",
      "critical_observations": "<1–2 sentences on form issues, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "stability": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "movement_quality": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences, or null>",
      "recommendation": "<one specific actionable cue>"
    },
    "range_of_motion": {
      "doing_well": "<1–2 sentences>",
      "critical_observations": "<1–2 sentences, or null>",
      "recommendation": "<one specific actionable cue>"
    }
  }
}
```

> **Why `null` not empty string for critical_observations:** An empty string (`""`) is ambiguous — did the model find no issues, or did it skip the field? `null` is an explicit signal that the model assessed this parameter and found nothing critical. This matters when scoring coaching quality programmatically.

> **Why structured output matters:** Prose responses cannot be scored programmatically. The `evidence` field forces the model to commit to a reason — this exposes hallucination (e.g., a model claiming to see knee cave from a side-view video where it is not visible).

---

## 8. Evaluation Scoring

Run each variant on all 6 videos. Score each fault detection as correct/incorrect against ground truth.

### Per-video scoring table (copy once per variant)

**Variant: ___________  |  Model: ___________  |  Date: ___________**

| Video | Fault | Ground Truth | Model Output | Correct? | Confidence | Latency (ms) |
|---|---|---|---|---|---|---|
| V1 | insufficient_depth | TRUE | | | | |
| V2 | insufficient_depth | FALSE | | | | |
| V3 | knee_valgus | TRUE | | | | |
| V4 | knee_valgus | FALSE | | | | |
| V5 | excessive_lean | TRUE | | | | |
| V6 | excessive_lean | FALSE | | | | |
| | | | **Total correct** | /6 | Avg: | Avg: |

### Coaching quality ratings (fill in blind — rate without knowing which variant)

Rate each parameter 1–5 using the rubric below. Do not look at variant labels while rating.

**Rubric:**
| Score | doing_well | critical_observations | recommendation |
|---|---|---|---|
| 5 | Specific and accurate | Pinpoints the exact fault with correct terminology | Single cue, directly addresses the fault, immediately actionable |
| 4 | Accurate but generic | Correct but vague ("knees moved inward") | Actionable but not specific to this person |
| 3 | Partially correct | Mentions something real but misses the main issue | Generic advice not tailored to observed fault |
| 2 | Inaccurate or irrelevant | Wrong fault identified | Contradicts observed data |
| 1 | Missing or empty | Null when a fault was clearly present | No recommendation given |

**Variant: ___________  |  Model: ___________  |  Date: ___________**

| Video | Posture /5 | Stability /5 | Movement Quality /5 | Range of Motion /5 | Avg /5 | Notes |
|---|---|---|---|---|---|---|
| V1 | | | | | | |
| V2 | | | | | | |
| V3 | | | | | | |
| V4 | | | | | | |
| V5 | | | | | | |
| V6 | | | | | | |
| **Average** | | | | | | |

---

## 9. Aggregate Results Table

Fill in after all runs are complete.

| Metric | Control | Variant A | Variant B | Variant D | Variant E |
|---|---|---|---|---|---|
| **Form accuracy (/6)** | | | | | |
| — Depth (/2) | | | | | |
| — Knee tracking (/2) | | | | | |
| — Torso (/2) | | | | | |
| **Avg latency (ms)** | | | | | |
| — p95 latency (ms)** | | | | | |
| **Coaching quality — Posture (/5)** | | | | | |
| **Coaching quality — Stability (/5)** | | | | | |
| **Coaching quality — Movement Quality (/5)** | | | | | |
| **Coaching quality — Range of Motion (/5)** | | | | | |
| **Coaching quality — Average (/5)** | | | | | |
| **Cost per video (USD)** | | | | | |

---

## 10. Decision Framework

Use this to pick a winner after results are in.

**Step 1 — Eliminate on form accuracy**  
Any variant scoring ≤ 3/6 (≤ 50%) is disqualified regardless of latency or coaching quality.

**Step 2 — Check the knee tracking split**  
Compare V3/V4 scores across variants specifically. If visual variants don't beat the Control on knee tracking, visual input is not justified for this fault type.

**Step 3 — Apply latency constraint**  
If Variant B (video) scores the same as Variant A (frames) on form accuracy, prefer A — it will almost always be faster and cheaper. Apply the same logic to D vs E: if accuracy is equal, prefer the lower-latency option.

**Step 4 — Cost/accuracy tradeoff**  
Calculate cost per video for each variant. If the delta in form accuracy between Control and the best visual variant is 1 correct call (e.g., 5/6 vs 6/6), document the cost per marginal improvement for the product decision.

**Step 5 — Check confidence calibration**  
A good model is confident when correct and uncertain when wrong. Plot `confidence` vs `correct` per variant. A model that reports 0.9 confidence on wrong answers is dangerous for a health/coaching product.

---

## 11. Run Checklist

**Setup**
- [ ] Film 6 videos per spec in Section 5
- [ ] Run MediaPipe on all 6 → extract JSON per video
- [ ] Fill in ground truth labels table (Section 5)
- [ ] Fill in fault thresholds (Section 6)
- [ ] Confirm NVIDIA NIM API key works (llama-3.1-70b and llama-3.2-90b-vision)
- [ ] Obtain Google AI API key for Gemini 2.0 Flash
- [ ] Implement key-frame extraction for Variant A
- [ ] Confirm MediaPipe pipeline outputs processed videos to `processed_videos/` with correct naming (`v1_depth_fault_processed.mp4` etc.)

**Execution**
- [ ] Run Control on all 6 videos — log outputs + latency
- [ ] Run Variant A on all 6 videos — log outputs + latency
- [ ] Run Variant B on all 6 videos — log outputs + latency
- [ ] Run Variant D on all 6 videos — log outputs + latency
- [ ] Run Variant E on all 6 videos — log outputs + latency
- [ ] (Optional) Run Variant C on all 6 videos if Nemotron access confirmed

**Evaluation**
- [ ] Fill in per-video scoring tables (Section 8)
- [ ] Rate coaching quality blind (do not look at variant labels while rating)
- [ ] Fill in aggregate results table (Section 9)
- [ ] Apply decision framework (Section 10)
- [ ] Document winner + rationale for team

---

## 12. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Small test set (6 videos) | Results may not generalise to diverse body types, lighting, clothing | Treat as directional signal, not final benchmark. Expand to 20+ videos before production decision. |
| Single subject | Confounds body-type variance | Film multiple people if possible for validation set |
| Frontal vs sagittal split | Knee tracking only testable from front; depth/torso only testable from side | Document this explicitly in results — do not compare knee tracking scores from a side-view video |
| Variant B uses different model family | Video quality improvement may reflect model quality, not modality | Add GPT-4o as image variant to cross-check if budget allows |
| Deliberate/exaggerated faults | Real-world faults are subtler | Re-run with subtle fault videos after pipeline is validated |
