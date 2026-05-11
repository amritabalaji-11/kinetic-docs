# Kinetic — Frontend Response Schemas
**Task:** S1-W5-03  
**Last updated:** May 11, 2026  
**Scope:** Form analysis result · Form comparison  
**Deferred (post-demo):** Auth · User profile  
**Excludes:** SSE events (defined separately in S1-W5-06a)

---

## 1. Form Analysis Result
**Endpoint:** `GET /analysis/{id}/result`  
**When:** User navigated to Results screen after `analysis_complete` SSE fires

```json
{
  "analysis_id": "uuid",
  "exercise": "Goblet Squat",
  "weight_value": 20.0,
  "weight_unit": "kg",
  "rep_count": 10,
  "created_at": "2026-05-09T10:32:00Z",
  "quality_gate_status": "GOOD",

  "overall_score": 72,

  "annotated_frame_url": "https://storage.googleapis.com/kinetic-videos/analyses/{analysis_id}/worst_rep_frame.jpg",

  "coaching": {
    "summary_paragraph": "At 20kg your depth is consistent and back angle holds well across most reps, but your descent is too fast — dropping rather than controlling the movement, which compounds from rep 7 onwards.",

    "parameters": {
      "posture": {
        "score": 68,
        "affirmation": null,
        "observation": null,
        "correction": "Brace your core before each descent and keep your chest tall as you approach depth."
      },
      "stability": {
        "score": 80,
        "affirmation": null,
        "observation": null,
        "correction": "Drive your knees outward in line with your pinky toe as you begin to rise."
      },
      "movement_quality": {
        "score": 85,
        "affirmation": null,
        "observation": null,
        "correction": "Try elevating heels slightly if ankle tightness limits depth in later reps."
      },
      "tempo": {
        "score": 55,
        "affirmation": null,
        "observation": null,
        "correction": "Aim for at least 1.5s on the lowering phase — think slow lower, fast drive up."
      }
    }
  },

  "reps": [
    { "rep_number": 1,  "form_score": 78 },
    { "rep_number": 2,  "form_score": 77 },
    { "rep_number": 3,  "form_score": 76 },
    { "rep_number": 4,  "form_score": 75 },
    { "rep_number": 5,  "form_score": 70 },
    { "rep_number": 6,  "form_score": 72 },
    { "rep_number": 7,  "form_score": 69 },
    { "rep_number": 8,  "form_score": 68 },
    { "rep_number": 9,  "form_score": 65 },
    { "rep_number": 10, "form_score": 63 }
  ]
}
```

**Frontend rendering notes:**
- `annotated_frame_url` — single image: worst-rep bottom-position frame with joint angle overlay. Shown as visual proof on Results screen.
- `coaching.parameters.[x].affirmation` and `.observation` — `null` in W6/W7. Rendered only when non-null. Design iteration W7/8.
- `coaching.parameters.[x].correction` — always present at W7. Shown as the "action to work on" card.
- `reps` — plotted as rep-by-rep score chart (x: rep_number, y: form_score).
- `quality_gate_status` — surface soft confidence warning on Results screen if `ACCEPTABLE`.

---

## 2. Form Comparison
**Endpoint:** `GET /analysis/{id}/comparison`  
**When:** User opens Form Comparison tab on Results screen  
**Pre-generated:** Yes — generated async after `analysis_complete` fires, stored to DB. Tab loads instantly.  
**Logic:** Current analysis vs latest previous completed analysis for same `exercise_id` + `user_id`

### 2a. Has previous session

```json
{
  "has_comparison": true,
  "empty_state_message": null,

  "current": {
    "analysis_id": "uuid",
    "date": "2026-05-09",
    "exercise": "Goblet Squat",
    "weight_value": 20.0,
    "weight_unit": "kg",
    "overall_score": 72,
    "annotated_frame_url": "https://storage.googleapis.com/.../current_worst_rep_frame.jpg",
    "rep_scores": [78, 77, 76, 75, 70, 72, 69, 68, 65, 63],
    "parameters": {
      "posture":          68,
      "stability":        80,
      "movement_quality": 85,
      "tempo":            55
    }
  },

  "previous": {
    "analysis_id": "uuid",
    "date": "2026-04-25",
    "exercise": "Goblet Squat",
    "weight_value": 15.0,
    "weight_unit": "kg",
    "overall_score": 65,
    "annotated_frame_url": "https://storage.googleapis.com/.../previous_worst_rep_frame.jpg",
    "rep_scores": [70, 68, 72, 69, 65, 64, 61],
    "parameters": {
      "posture":          60,
      "stability":        75,
      "movement_quality": 80,
      "tempo":            48
    }
  },

  "comparison_coaching": {
    "summary_paragraph": "Your form has improved 7 points since your last session at 15kg — posture and tempo both moved in the right direction as you stepped up the weight.",
    "parameters": {
      "posture":          { "observation_action": "Back angle is more controlled at 20kg — keep bracing before each descent as weight increases." },
      "stability":        { "observation_action": "Knee stability has improved but watch for cave on the ascent at heavier loads." },
      "movement_quality": { "observation_action": "Depth is consistent at heavier weight — ankle mobility holding well." },
      "tempo":            { "observation_action": "Still dropping on the descent — controlling this will be critical at your next weight step." }
    }
  }
}
```

### 2b. No previous session

```json
{
  "has_comparison": false,
  "empty_state_message": "You haven't done a previous Goblet Squat analysis yet. Upload another session to unlock comparison.",
  "current": null,
  "previous": null,
  "comparison_coaching": null
}
```

**Frontend rendering notes:**
- **Parameter variance** — calculated frontend: `current.parameters.[x] − previous.parameters.[x]`. Display as `+8` (green) or `−3` (orange) inline next to the current score.
- **Performance Over Reps %** — calculated frontend: `(Σ current rep_scores − Σ previous rep_scores) ÷ Σ previous rep_scores × 100`. Display as e.g. `+8.3%` or `−2.1%`.
- **Rep chart** — overlay both `rep_scores` arrays on the same chart (x: rep number, y: form score). Arrays may differ in length — plot at natural length, no padding.
- **Overall score variance** — calculated frontend: `current.overall_score − previous.overall_score`.
- `annotated_frame_url` per session — worst-rep bottom frame (one per analysis).

**Backend async generation:**
```
After analysis_complete SSE fires (non-blocking):
  1. Query DB: latest previous completed analysis for same exercise_id + user_id
  2a. Found → call Claude with current + previous Nemotron outputs + user history
              → store result in form_analysis_results.comparison_coaching_output (jsonb)
              → fire comparison_ready SSE → { analysis_id, session_id, user_id }
  2b. Not found → store has_comparison: false immediately
  Frontend: listens for comparison_ready SSE → enables comparison tab
  Edge case: tab opened < 5s after results → show brief loading state
```

---

## 3. Auth — Deferred (post-demo)

Auth (JWT + Supabase Auth) is **dropped from MVP scope**. No login or signup screens, no auth endpoints, no JWT middleware built for demo.

**For demo:** 2–3 `user_id` values are hardcoded in the DB (e.g. `user_001`, `user_002`). Frontend sends a fixed `user_id` header on all requests. Form comparison, session history, and progression work normally.

**Post-demo:** Full Supabase Auth + Google OAuth to be added after launch.

---

## 4. User Profile — Deferred (post-demo)

`GET /users/profile` and `POST /users/profile` endpoints are **not built for demo**.

**For demo:** Profile screen exists as a routable frontend shell with dummy data. No backend calls made.

**Post-demo:** Full profile endpoints to be added after launch.

---

## 5. DB Fields Required

### `form_analysis_results` — fields written during pipeline

| Field | Type | Written by | Notes |
|---|---|---|---|
| `annotated_frame_url` | string · nullable | Squad 2 — after OpenCV Step 5b | GCS URL of worst-rep bottom frame with joint angle overlay. NULL until frame extraction completes. |
| `comparison_coaching_output` | jsonb · nullable | Squad 2 — async after analysis_complete | Full comparison_coaching block. NULL if no previous session exists or generation pending. |

### New table — `gold_standard_biomechanics`

Populated in W6 data prep. 3–5 good-form Goblet Squat reference videos run through MediaPipe + biomechanics script. Used by OpenCV Part 2 overlay (gold standard angle ranges) and Claude system prompt (reference values).

---

## Changelog
- May 9, 2026: Initial definition — form analysis, comparison, auth, user profile
- May 11, 2026: Sync with technical_data_schema.html — weight_value/unit split, single annotated_frame_url, coaching structure, comparison_coaching, variance moved to frontend, performance_over_reps_pct added, auth + profile marked deferred, DB section updated
