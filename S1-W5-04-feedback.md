# S1-W5-04 — Fixture Review Feedback
**Task:** Build dummy data fixtures matching schema  
**Date:** May 12, 2026  
**Status:** Accept with fixes — 5 items below before AC sign-off

---

## What's good

- SSE sequence (13 events + error splice) — correct and complete
- `retryable` as string enum (`"true"` / `"false"` / `"partial"`) — keep this
- `form-comparison.json` — great initiative, accepted (same-weight scenario is valid)
- `validate-fixtures.js` — good addition
- 2 form analysis fixtures (with-issues + clean) + progression recommendations — covers the AC

---

## Fix 1 — Add a failed upload fixture

The SSE error splice covers the *event*. The `Failed_Upload_Scan_Screen` also needs a static fixture showing the full error state the screen renders from. Create `form-analysis.failed.json`:

```json
[
  {
    "scenario": "M2 — both sides not visible",
    "analysis_id": "uuid-fail-001",
    "status": "failed",
    "error_code": "CRITICAL_OCCLUSION",
    "error_stage": "mediapipe",
    "retryable": "false",
    "title": "We couldn't see your lower body clearly",
    "message": "Your camera may be facing you from directly to your side or slightly behind you. Try angling it slightly toward the front of your body so both legs are fully in view throughout the squat.",
    "cta_label": "Re-film — see tips"
  },
  {
    "scenario": "M6 — too few reps",
    "analysis_id": "uuid-fail-002",
    "status": "failed",
    "error_code": "INSUFFICIENT_REPS",
    "error_stage": "mediapipe",
    "retryable": "false",
    "title": "Film a full set to get your analysis",
    "message": "We need at least 3 complete reps to give you meaningful feedback. Squat all the way down and all the way back up for each one — don't stop at 1 or 2.",
    "cta_label": "Re-film"
  },
  {
    "scenario": "M4 — poor composite score",
    "analysis_id": "uuid-fail-003",
    "status": "failed",
    "error_code": "POOR_COMPOSITE",
    "error_stage": "mediapipe",
    "retryable": "false",
    "title": "We couldn't read your body position clearly",
    "message": "This usually happens when filming from behind, with something blocking the view, or in low lighting. Film from your side with good lighting and a clear background.",
    "cta_label": "Re-film — see tips"
  },
  {
    "scenario": "M7 — acceptable quality, pass with inline warning",
    "analysis_id": "uuid-warn-001",
    "status": "complete",
    "error_code": "ACCEPTABLE",
    "error_stage": null,
    "retryable": "partial",
    "title": "Results may be slightly less accurate",
    "message": "Some parts of your form were harder to read than usual. Try filming closer to the guidelines next time for a sharper analysis.",
    "cta_label": null
  }
]
```

**Rendering rules:**
- `retryable: "false"` → show Re-film prompt (blocking error screen)
- `retryable: "partial"` → show as a dismissible inline note on Results screen, not a blocking screen

---

## Fix 2 — Add `tempo` to all form analysis fixtures

The 4 parameters are: Posture · Stability · Movement Quality · **Tempo**. `tempo_score` is missing from the fixtures and the schema fields section in the README. Add it to all `form-analysis.*.json` fixtures:

```json
"coaching": {
  "parameters": {
    "posture":          { "score": 68, "affirmation": null, "observation": null, "correction": "..." },
    "stability":        { "score": 80, "affirmation": null, "observation": null, "correction": "..." },
    "movement_quality": { "score": 85, "affirmation": null, "observation": null, "correction": "..." },
    "tempo":            { "score": 55, "affirmation": null, "observation": null, "correction": "..." }
  }
}
```

> `affirmation` and `observation` are `null` now — they are W7/8 iteration fields. Only `score` and `correction` are needed at W6.

---

## Fix 3 — Field naming: align to `FE_Response_Schemas.md`

Sharing the updated schema doc separately. Make these renames across all fixtures:

### Form Analysis fixtures (`form-analysis.*.json`)

| Currently | Change to |
|---|---|
| `coaching_output.summary_paragraph` | `coaching.summary_paragraph` |
| `coaching_output.issues[].cue` | `coaching.parameters.[x].correction` — one correction string per parameter, not per issue |
| `coaching_output.issues[].drill` | **Remove** — not in schema |
| `weight_kg: 40` | `weight_value: 40, weight_unit: "kg"` |
| `progression.suggested_weight_kg` | `progression.suggested_weight_value` + `progression.suggested_weight_unit` |
| `issues_json` | **Check with Squad 2** — this field is not in `FE_Response_Schemas.md`, clarify what it maps to before keeping it |
| `weight_kg_normalised` | **Check with Squad 2** — not in schema, confirm where this comes from |

### Form Comparison fixture (`form-comparison.json`)

| Currently | Change to |
|---|---|
| `verdict` (top-level string) | `comparison_coaching.summary_paragraph` |
| `parameter_tips.posture` | `comparison_coaching.parameters.posture.observation_action` |
| `parameter_tips.stability` | `comparison_coaching.parameters.stability.observation_action` |
| `parameter_tips.movement_quality` | `comparison_coaching.parameters.movement_quality.observation_action` |
| `parameter_tips.tempo` | `comparison_coaching.parameters.tempo.observation_action` |
| `current.weight_kg` | `current.weight_value` + `current.weight_unit` |
| `previous.weight_kg` | `previous.weight_value` + `previous.weight_unit` |
| `variance` block | **Remove from fixture** — variance is calculated frontend, not returned by backend |

---

## Fix 4 — Case 2 empty state message exact copy

The `empty_state_message` value in `form-comparison.json` (Case 2 — no previous session) must be exactly:

```json
{
  "has_comparison": false,
  "empty_state_message": "Sorry you do not have any past form analysis done before this session. Try the next time you do a form analysis",
  "current": null,
  "previous": null,
  "comparison_coaching": null
}
```

---

## Fix 5 — Document % per SSE event for progress bar

The Processing screen shows a progress bar that advances with each SSE event. The SSE sequence fixture has 13 events but doesn't map each event to a percentage. Add a `progress_pct` field to each event in `sse-upload-progress.sequence.json` so Squad 1 can implement the bar consistently. Suggested mapping:

| SSE Event | `progress_pct` |
|---|---|
| `upload_received` | 5 |
| `mediapipe_started` | 10 |
| `mediapipe_complete` | 25 |
| `biomechanics_complete` | 40 |
| `nemotron_started` | 45 |
| `nemotron_complete` | 60 |
| `frames_extracting` | 65 |
| `frames_ready` | 75 |
| `rag_started` | 78 |
| `rag_complete` | 82 |
| `claude_started` | 85 |
| `claude_complete` | 95 |
| `analysis_complete` | 100 |

> Adjust percentages if they don't feel right visually — the important thing is Squad 1 uses one agreed mapping, not each engineer deciding their own.

---

## Notes (no fix needed)

- **Exercise name (Barbell Squat):** MVP exercise is Goblet Squat — update fixture `exercise` field to `"Goblet Squat"` when convenient, but not a blocker.
- **Auth fixture:** `auth.response.json` — auth is dropped from MVP scope. Remove this file to avoid confusion. Auth will be added post-demo.
- **`annotated_frame_url` 404s in dev:** already noted in README — keep the fallback placeholder approach, that's correct.

---

## Before closing AC

Confirm the Results screen shell renders using fixture data without console errors (AC criterion 5). Screenshot or a brief note is enough.
