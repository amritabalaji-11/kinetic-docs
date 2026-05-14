# Kinetic — Frontend Response Schemas
**Task:** S1-W5-03  
**Last updated:** May 12, 2026  
**Scope:** Upload POST body · Form analysis result · Form comparison  
**Deferred (post-demo):** Auth · User profile  
**Excludes:** SSE events (defined separately in S1-W5-06a)

---

## Pipeline Overview

Who owns what, and what passes between squads at each handoff.

| Step | Name | Owned by | Input | Output / Handoff |
|---|---|---|---|---|
| — | User uploads video | **S1 — Frontend** | User action | POST body → S2 (see Section 0) |
| 1–2 | GCS Storage + DB Write | **S2 — Backend** | POST body | `analysis_id` generated · video stored · SSE stream opened |
| 3–4 | Pose Detection + Biomechanics | **S3 — AI/MediaPipe** | `video_url` (GCS) | Biomechanics JSON → S2 |
| 5 | Nemotron Analysis | **S2 + S3** | Video frames + Biomechanics JSON | Issues JSON · scores · chain of thought → S2 |
| 5b | Frame Extraction (OpenCV) | **S2 — Backend** | `video_url` | `annotated_frame_url` written to DB |
| 6 | RAG Retrieval | **S2 — Backend** | Issue tags from Nemotron | Research passages for Claude prompt |
| 7 | Claude Sonnet Coaching | **S2 — Backend** | Nemotron output + RAG + user history | `coaching_output` + `progression_recommendation` → DB |
| 8a | Results Screen | **S1 — Frontend** | `analysis_complete` SSE | `GET /analysis/{id}/result` → renders results (Section 1) |
| 8b | Form Comparison | **S1 — Frontend** | `comparison_ready` SSE | `GET /analysis/{id}/comparison` → renders comparison (Section 2) |

---

## 0. Upload POST Body (S1 → S2)
**Endpoint:** `POST /upload`  
**Format:** `multipart/form-data`  
**When:** User submits video on Upload screen

```json
{
  "video":        "<file>",
  "exercise_id":  "ex_gob_squat_001",
  "weight_value": 20.0,
  "weight_unit":  "kg",
  "user_id":      "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "session_id":   "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
}
```
> `analysis_id` is **not sent** — generated server-side via `uuid4()`.

**Field Reference**

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `video` | file | No | max 500 MB | `mp4` / `mov` | Validate size and file type before submit. Show error if invalid. |
| `exercise_id` | uuid | No | fixed set | — | MVP: always `ex_gob_squat_001`. Read from exercises reference table. |
| `weight_value` | float | No | 0.5 – 999.9 | 1 dp | Validate > 0 before submit. User enters this. |
| `weight_unit` | enum | No | `kg` \| `lb` | — | User's unit preference. Stored as-is. |
| `user_id` | uuid | No | 36 chars | — | **Hardcoded in frontend** — one of 3 fixed values (`user_001`, `user_002`, `user_003`) pre-seeded in DB. Auth de-scoped — no login for demo. |
| `session_id` | uuid | No | 36 chars | — | From `sessionStorage`. Generated at app mount via `crypto.randomUUID()`. Clears when tab closes. **Auth de-scoped — was from JWT.** |

---

## 1. Form Analysis Result
**Endpoint:** `GET /analysis/{id}/result`  
**Produced by:** S2 — Backend  
**Consumed by:** S1 — Frontend  
**When:** User navigates to Results screen after `analysis_complete` SSE fires

**Field availability by week** — same endpoint, same shape throughout. Null fields fill in as pipeline stages complete. S1 renders non-null fields and shows placeholders for null.

| Field | W6 (biomechanics only) | W7 (+ LLM) | W8 (+ progression logic) |
|---|---|---|---|
| `overall_score` | ✓ from biomechanics | ✓ | ✓ |
| `rep_count`, `reps[]` | ✓ from biomechanics | ✓ | ✓ |
| `quality_gate_status` | ✓ | ✓ | ✓ |
| `coaching.*` | null | ✓ | ✓ |
| `progression_recommendation` | null | null | ✓ |
| `annotated_frame_url` | null | ✓ | ✓ |

```json
{
  "analysis_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "exercise": "Goblet Squat",
  "weight_value": 20.0,
  "weight_unit": "kg",
  "rep_count": 10,
  "created_at": "2026-05-09T10:32:00Z",
  "quality_gate_status": "GOOD",

  "overall_score": 72,
  "progression_recommendation": "hold",

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

**Field Reference**

| Field | Type | Nullable | Range / Max | Format | FE Display Note |
|---|---|---|---|---|---|
| `analysis_id` | uuid | No | 36 chars | — | Used to construct comparison endpoint URL. Not displayed. |
| `exercise` | string | No | max 50 chars | — | Display as screen heading. e.g. "Goblet Squat" |
| `weight_value` | float | No | 0.5 – 999.9 | 1 dp · strip trailing zero | Show with unit inline. "20kg" not "20.0 kg" |
| `weight_unit` | enum | No | `kg` \| `lb` | — | Always render alongside `weight_value` |
| `rep_count` | integer | No | 1 – 99 | — | Display as "10 reps" |
| `created_at` | timestamp | No | — | `D MMM YYYY` | Drop the time. e.g. "9 May 2026" |
| `quality_gate_status` | enum | Yes | `GOOD` \| `ACCEPTABLE` | — | Show soft confidence warning banner **only** if `ACCEPTABLE`. Hide entirely if `GOOD` or null. |
| `overall_score` | integer | No | 0 – 100 | — | Large display number. No decimal. No % symbol. DB column is `overall_form_score` — serialised as `overall_score` in this response. |
| `progression_recommendation` | enum | **Yes** (null until W7) | `hold` \| `progress` \| `drop` | — | Null until Claude step completes (W7+). Display as progression card on Results screen. `hold` = stay at current weight · `progress` = ready to increase · `drop` = reduce weight. |
| `annotated_frame_url` | url | **Yes (V2)** | — | — | Show image skeleton placeholder if null. Render image on load. |
| `coaching.summary_paragraph` | string | No | max 400 chars | — | Full-width text block. No truncation. Allow wrap. |
| `coaching.parameters.[x].score` | integer | No | 0 – 100 | — | One score per parameter card (posture / stability / movement_quality / tempo) |
| `coaching.parameters.[x].affirmation` | string | **Yes** | max 200 chars | — | Null in W6/W7. **Only render the element when non-null.** Design iteration W8. |
| `coaching.parameters.[x].observation` | string | **Yes** | max 200 chars | — | Null in W6/W7. **Only render the element when non-null.** Design iteration W8. |
| `coaching.parameters.[x].correction` | string | **Yes** | max 300 chars | — | Always present at W7+. Display as "Action" card on parameter. |
| `reps[].rep_number` | integer | No | 1 – 99 | — | x-axis label on rep chart |
| `reps[].form_score` | integer | No | 0 – 100 | — | y-axis value on rep chart. Fix y-axis range to 0–100. |

---

## 2. Form Comparison
**Endpoint:** `GET /analysis/{id}/comparison`  
**Produced by:** S2 — Backend  
**Consumed by:** S1 — Frontend  
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

**Field Reference — top level**

| Field | Type | Nullable | Range / Max | Format | FE Display Note |
|---|---|---|---|---|---|
| `has_comparison` | boolean | No | — | — | Controls which state to render. `false` → show empty state. `true` → show comparison view. |
| `empty_state_message` | string | **Yes** | max 200 chars | — | Only shown when `has_comparison` is `false`. Null when `true`. |
| `current` | object | **Yes** | — | — | Null only when `has_comparison` is `false` |
| `previous` | object | **Yes** | — | — | Null only when `has_comparison` is `false` |
| `comparison_coaching` | object | **Yes** | — | — | Null only when `has_comparison` is `false` |

**Field Reference — `current` and `previous` (identical structure)**

| Field | Type | Nullable | Range / Max | Format | FE Display Note |
|---|---|---|---|---|---|
| `analysis_id` | uuid | No | 36 chars | — | Not displayed. Used internally if needed. |
| `date` | date | No | — | `D MMM YYYY` | Column header in comparison view. e.g. "9 May 2026" |
| `exercise` | string | No | max 50 chars | — | Always identical in both objects — display once as shared heading, not per column. |
| `weight_value` | float | No | 0.5 – 999.9 | 1 dp · strip trailing zero | Show with unit inline per column. e.g. "20kg" / "15kg" |
| `weight_unit` | enum | No | `kg` \| `lb` | — | Always render alongside `weight_value` |
| `overall_score` | integer | No | 0 – 100 | — | Large number per column. Show FE-calculated variance inline: `+7` green · `−3` orange. |
| `annotated_frame_url` | url | **Yes (V2)** | — | — | One frame per column. Show skeleton if null. |
| `rep_scores` | integer array | No | each: 0 – 100 | — | Overlay both arrays on the same chart. Arrays may differ in length — plot at natural length, **no padding**. |
| `parameters.posture` | integer | No | 0 – 100 | — | Show score + FE-calculated variance: `+8` green / `−3` orange |
| `parameters.stability` | integer | No | 0 – 100 | — | Same as posture |
| `parameters.movement_quality` | integer | No | 0 – 100 | — | Same as posture |
| `parameters.tempo` | integer | No | 0 – 100 | — | Same as posture |

> **FE-calculated fields (not in API response):**
> - Parameter variance: `current.parameters.[x] − previous.parameters.[x]`
> - Overall score variance: `current.overall_score − previous.overall_score`
> - Performance Over Reps %: `(Σ current rep_scores − Σ previous rep_scores) ÷ Σ previous rep_scores × 100` — display as e.g. `+8.3%` or `−2.1%`

**Field Reference — `comparison_coaching`**

| Field | Type | Nullable | Range / Max | Format | FE Display Note |
|---|---|---|---|---|---|
| `summary_paragraph` | string | **Yes** | max 400 chars | — | Full-width text block below the comparison table. Null when `has_comparison` is `false`. |
| `parameters.[x].observation_action` | string | **Yes** | max 300 chars | — | One text block per parameter. Null when `has_comparison` is `false`. |

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

Auth (JWT + Supabase Auth) is **dropped from MVP scope**. No login, signup, auth endpoints, or JWT middleware built for demo.

**For demo:** 3 `user_id` values are hardcoded in the frontend code (`user_001`, `user_002`, `user_003`) and pre-seeded in the DB. The frontend sends the active hardcoded `user_id` in the POST body. This lets the demo switch between users to show different progression histories. `session_id` is generated at app mount via `crypto.randomUUID()`, stored in `sessionStorage`, and sent in the POST body. No auth header or token required.

**Post-demo:** Full Supabase Auth + Google OAuth to be added after launch. `user_id` and `session_id` will revert to being extracted server-side from the JWT token.

---

## 4. User Profile — Deferred (post-demo)

`GET /users/profile` and `POST /users/profile` endpoints are **not built for demo**.

**For demo:** Profile screen exists as a routable frontend shell with dummy data. No backend calls made.

**Post-demo:** Full profile endpoints to be added after launch.

---

## 5. Session History, Dashboard & Workout Logger — Deferred (post-demo)

`GET /users/{id}/sessions`, `GET /users/{id}/dashboard`, `GET /users/{id}/workout-logs`, and `POST /users/{id}/workout-logs` endpoints are **not built for demo**.

**For demo:** All three screens exist as routable frontend shells with hardcoded dummy data. No backend API calls made. Dummy data should use the correct field names so wiring up real endpoints in W7+ requires only replacing fixtures, not refactoring components.

**Dummy data field names to use** (so components are wire-ready):

| Screen | Key fields in dummy data |
|---|---|
| Session History | `analysis_id` · `exercise` (display name) · `weight_value` · `weight_unit` · `created_at` · `overall_score` · `progression_recommendation` |
| Dashboard | Same as history (last 5) · `score_trend: [{ analysis_id, date, overall_score }]` |
| Workout Logger | `log_id` · `exercise_id` · `sets` · `reps` · `weight_value` · `weight_unit` · `analysis_id` (if linked) · `created_at` |

**Post-demo:** Full endpoints + response schemas to be added after launch.

---

## 6. DB Fields Required

### `form_analysis_results` — fields written during pipeline

| Field | Type | Written by | Notes |
|---|---|---|---|
| `annotated_frame_url` | string · nullable | S2 — after OpenCV Step 5b | GCS URL of worst-rep bottom frame with joint angle overlay. NULL until frame extraction completes. |
| `comparison_coaching_output` | jsonb · nullable | S2 — async after `analysis_complete` | Full `comparison_coaching` block. NULL if no previous session exists or generation pending. |

### Reference table — `exercises`

Seed table. Populated before W6. `exercise_id` is the FK used in `form_analyses` and `form_analysis_results`.

| Field | Type | Example | Notes |
|---|---|---|---|
| `exercise_id` | uuid (PK) | `ex_gob_squat_001` | Stable ID. Frontend sends this on upload. |
| `exercise_slug` | string | `goblet-squat` | Used for frontend routing |
| `display_name` | string | `Goblet Squat` | Used for UI rendering |
| `form_image_url` | string | GCS URL | Pre-upload guidance screen. Must be populated before S1-W6-02. |
| `camera_angle_tips` | string | `Position camera side-on...` | Shown on pre-upload guidance screen. |

### Reference table — `gold_standard_biomechanics`

Populated in W6 data prep. 3–5 good-form Goblet Squat reference videos run through MediaPipe + biomechanics script. Used by OpenCV Part 2 overlay (gold standard angle ranges) and Claude system prompt (reference values).

---

## Changelog
- May 9, 2026: Initial definition — form analysis, comparison, auth, user profile
- May 11, 2026: Sync with technical_data_schema.html — weight_value/unit split, single annotated_frame_url, coaching structure, comparison_coaching, variance moved to frontend, performance_over_reps_pct added, auth + profile marked deferred, DB section updated
- May 12, 2026: Added pipeline overview, Section 0 Upload POST body, field reference tables (type / nullable / range / format / FE display note) for all schemas, exercises reference table, auth section updated to reflect localStorage/sessionStorage approach (auth de-scoped)
