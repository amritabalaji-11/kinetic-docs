# Kinetic — Database Schema
**Last updated:** May 19, 2026 *(architecture update: Nemotron → Haiku 4.5, schema migration)*
**Scope:** All DB tables · field types · write timing · squad ownership
**Owner:** S2 — Backend defines and owns all DB schemas
**Related docs:** `FE_Response_Schemas.md` · `FE_SSE_and_Errors.md` · `technical_data_schema.html`

---

## Tables at a Glance

| Table | Type | Rows created | Written by |
|---|---|---|---|
| `form_analyses` | Job record | One per video upload | S2 — 3-step write pattern |
| `form_analysis_results` | AI output record | One per completed analysis | S2 — single INSERT + 2 async UPDATEs |
| `exercises` | Seed / reference | One per supported exercise | Manual seed — agreed cross-squad |
| `gold_standard_biomechanics` | Reference data | 2–5 per exercise | Manual — W7 data prep (S3) |

---

## Write Pattern Overview

> *(Updated May 19, 2026 — replaces old Nemotron Phase 1 / Claude Phase 2 pattern)*

| Pipeline step | What happens | Table | Write type |
|---|---|---|---|
| **Step 2** — Upload | Video stored to GCS | `form_analyses` | INSERT |
| **Step 3** — Quality gate | S3 returns keypoints + quality check | `form_analyses` | UPDATE (`quality_gate_status`, `video_score`) |
| **Step 5** — Haiku Call 1 complete | All scores + full coaching JSON written | `form_analysis_results` | INSERT (single write) |
| **Step 5** — Pipeline complete | S2 marks job done | `form_analyses` | UPDATE (`status = complete`) |
| **Step 5b** — OpenCV Part 2 complete | Worst-rep annotated frame ready | `form_analysis_results` | UPDATE (`annotated_frame_url`) |
| **Async after Step 5** — Haiku Call 2 | Longitudinal coaching for Tab 2 | `form_analysis_results` | UPDATE (`progression_output`) |

> **Why two tables?** `form_analyses` is the job record — exists from upload even if pipeline fails. `form_analysis_results` is the output record — only exists once Haiku Call 1 completes. A failed analysis leaves a `form_analyses` row with `status = failed` but no `form_analysis_results` row.

---

## 1. `form_analyses`

**Purpose:** Primary upload record. Created at upload. Tracks pipeline status.
**One row per:** Video upload
**PK:** `analysis_id`

### Write pattern

```
Step 2 — Upload
  INSERT: all fields except quality_gate_status, video_score (NULL)

Step 3 — Quality gate result received from S3
  UPDATE: quality_gate_status, video_score
  (if quality gate fails → status = failed, no further writes)

Step 5 — Haiku Call 1 complete / pipeline done
  UPDATE: status = complete
```

### Field Reference

| Field | Type | Nullable | Format | Written by | Step |
|---|---|---|---|---|---|
| `analysis_id` | uuid (PK) | No | — | S2 — `uuid4()` at upload | Step 2 INSERT |
| `session_id` | uuid | No | — | S1 → from sessionStorage, sent in POST | Step 2 INSERT |
| `user_id` | uuid | No | — | S1 → one of `user_001`, `user_002`, `user_003` (demo IDs). Auth de-scoped. | Step 2 INSERT |
| `exercise_id` | uuid (FK → exercises) | No | — | S1 → sent in POST body | Step 2 INSERT |
| `weight_value` | float | No | 1 dp | S1 → sent in POST body | Step 2 INSERT |
| `weight_unit` | enum | No | `kg` \| `lb` | S1 → sent in POST body | Step 2 INSERT |
| `weight_kg_normalised` | float | No | 4 dp | S2 — computed at upload | Step 2 INSERT |
| `video_url` | string (GCS URI) | No | `gs://kinetic-videos/videos/{user_id}/{analysis_id}/original.mp4` | S2 — constructed after GCS upload | Step 2 INSERT |
| `created_at` | timestamp | No | ISO 8601 UTC | S2 — server time | Step 2 INSERT |
| `status` | enum | No | `uploaded` \| `processing` \| `complete` \| `failed` | S2 | Step 2 INSERT → Step 5 UPDATE |
| `quality_gate_status` | enum | **Yes** (NULL until Step 3) | `GOOD` \| `ACCEPTABLE` | S2 — from quality gate result | Step 3 UPDATE |
| `video_score` | numeric(4,3) | **Yes** (NULL until Step 3) | 0.000–1.000 | S2 — composite landmark visibility score | Step 3 UPDATE |

---

## 2. `form_analysis_results`

**Purpose:** Full Haiku Call 1 output. Created in a single INSERT when Haiku completes. Updated asynchronously by OpenCV Part 2 (annotated frame) and Haiku Call 2 (progression output for Tab 2).
**One row per:** Completed analysis
**PK:** `analysis_id` (same as `form_analyses`)

### Write pattern

```
Step 5 — Haiku Call 1 complete (single INSERT — all at once)
  INSERT: identity + weight + all scores + all analysis columns + coaching_output
  annotated_frame_url = NULL  (written by OpenCV Part 2)
  progression_output  = NULL  (written by Haiku Call 2 async)

Step 5b — OpenCV Part 2 complete (~2–3s after Haiku)
  UPDATE: annotated_frame_url = <GCS URI of worst-rep annotated frame>

Async after Step 5 — Haiku Call 2 longitudinal coaching
  UPDATE: progression_output = <Section 1 + Section 2 JSON for Tab 2>
  (only runs if a previous completed analysis exists for same exercise_id + user_id)
```

> **Note on causal reasoning:** Haiku's reasoning is captured in the `causal_chain` flat column. No separate `chain_of_thought` column — causal chain is structured and queryable, not free text.

---

### Field Reference — Identity & Weight

| Field | Type | Nullable | Written by | Step |
|---|---|---|---|---|
| `analysis_id` | uuid (PK) | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `session_id` | uuid (FK) | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `user_id` | uuid | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `exercise_id` | uuid (FK → exercises) | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `weight_value` | float | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `weight_unit` | enum | No | S2 — copied from `form_analyses` | Step 5 INSERT |
| `weight_kg_normalised` | float | No | S2 — copied from `form_analyses` | Step 5 INSERT |

---

### Field Reference — Session-level Scores (flat columns for fast querying)

> *(Updated May 19, 2026 — source changed from Nemotron to Haiku Call 1; `tempo_score` renamed to `range_of_motion_score`)*

Source: Haiku Call 1 output. Stored flat so Haiku Call 2 can compare across sessions without parsing JSONB.

| Field | Type | Nullable | Range | Written by | Step |
|---|---|---|---|---|---|
| `overall_form_score` | integer | No | 0–100 | S2 — from Haiku Call 1 (`total_score`) | Step 5 INSERT |
| `posture_score` | integer | No | 0–100 | S2 — from Haiku Call 1 | Step 5 INSERT |
| `stability_score` | integer | No | 0–100 | S2 — from Haiku Call 1 | Step 5 INSERT |
| `movement_quality_score` | integer | No | 0–100 | S2 — from Haiku Call 1 | Step 5 INSERT |
| `range_of_motion_score` | integer | No | 0–100 | S2 — from Haiku Call 1. *🆕 Added May 19 — renamed from `tempo_score`* | Step 5 INSERT |

---

### Field Reference — Rep-level Scores *(Updated May 19 — per-rep format now includes all 4 parameter scores)*

| Field | Type | Nullable | Format | Written by | Step |
|---|---|---|---|---|---|
| `rep_count` | integer | No | 1–99 | S2 — from Haiku Call 1 | Step 5 INSERT |
| `worst_rep_index` | integer | No | 0–98 (0-based array index) | S2 — Haiku calculates and returns this in db_output. The 0-based array index of the rep with the lowest overall score from `rep_scores`. S2 writes it directly to DB. OpenCV Part 2 uses this to extract the worst-performing rep for frame annotation. | Step 5 INSERT |
| `rep_scores` | jsonb array | No | See format below | S2 — from Haiku Call 1. OpenCV Part 2 reads this to find the lowest-scoring rep for frame extraction. | Step 5 INSERT |

**`rep_scores` format:**
```json
[
  { "rep_number": 1, "overall": 82, "posture": 84, "stability": 75, "movement_quality": 85, "range_of_motion": 78 },
  { "rep_number": 2, "overall": 79, "posture": 80, "stability": 71, "movement_quality": 83, "range_of_motion": 75 }
]
```

---

### Field Reference — Fault Detection (flat columns for fast querying)

> *(Added May 19, 2026 — replaces old `issues_json` Nemotron format. All 5 columns below are new.)*

Source: Haiku Call 1 output. Stored flat so Haiku Call 2 can query fault history across sessions.

| Field | Type | Nullable | Format | Written by | Step |
|---|---|---|---|---|---|
| `issue_tags` | text[] + GIN index | No | `["knee_valgus"]` | S2 — extracted from `faults_detected` where value = true. | Step 5 INSERT |
| `faults_detected` | jsonb | No | See format below | S2 — from Haiku Call 1 (`db_output.faults_detected`). | Step 5 INSERT |
| `fault_confidence` | jsonb | No | See format below | S2 — Haiku certainty per fault EXISTS (0.0–1.0). *🆕 Renamed May 21 from `confidence`* | Step 5 INSERT |
| `causal_chains` | jsonb array | No | See format below | S2 — array of root cause objects. Supports multiple independent root causes. *🆕 Renamed + type changed May 21 from `causal_chain` object* | Step 5 INSERT |
| `camera_angle` | enum | No | `"side" \| "front"` | S2 — echoed from `biomechanics_json.camera_angle`. Required by OpenCV Part 2 for gold standard matching. *🆕 Added May 21* | Step 5 INSERT |
| `fault_detail` | jsonb | No | See format below | S2 — per-fault detail. **Key field for longitudinal progression.** | Step 5 INSERT |
| `trends` | jsonb | No | `{ "worsening": [...], "improving": [...], "stable": [...] }` | S2 — session-level direction summary. | Step 5 INSERT |
| `reasoning` | string | No | Max 200 words | S2 — Haiku chain-of-thought from `db_output.reasoning`. Stored for debugging and model improvement. *🆕 Added May 21* | Step 5 INSERT |

**Issue tag vocabulary (fixed set):** `insufficient_depth` · `knee_valgus` · `excessive_forward_lean`

GIN index queries:
```sql
WHERE 'knee_valgus' = ANY(issue_tags)
WHERE issue_tags @> ARRAY['knee_valgus','insufficient_depth']
```

**`faults_detected` format:**
```json
{
  "insufficient_depth": false,
  "knee_valgus": true,
  "excessive_forward_lean": false
}
```

**`fault_confidence` format** *(renamed from `confidence` May 21 — certainty that each fault EXISTS):*
```json
{
  "insufficient_depth": 0.90,
  "knee_valgus": 0.85,
  "excessive_forward_lean": 0.92
}
```

**`causal_chains` format** *(renamed + type changed May 21 — now a JSONB array supporting multiple independent root causes):*
```json
[
  {
    "root_cause": "ankle_restriction",
    "chain": "ankle restriction → forward lean → depth deficit",
    "explanation": "Limited dorsiflexion forces the torso forward, preventing full hip depth.",
    "causal_confidence": 0.75,
    "confidence_note": "Valgus could be independent glute weakness — distinguishing signal: valgus present from rep 1",
    "affected_parameters": ["range_of_motion", "posture"]
  }
]
```

> `causal_confidence` = certainty of the root cause **attribution** (distinct from `fault_confidence` which measures whether the fault exists). Multiple entries when two independent root causes are identified.

**`fault_detail` format (one object per fault — key field for progression):**
```json
{
  "insufficient_depth": {
    "present": false,
    "reps_affected": "0 of 8",
    "which_reps": [],
    "severity": "knee_angle_min 88° — within range",
    "trend": "stable",
    "source": "json"
  },
  "knee_valgus": {
    "present": true,
    "reps_affected": "6 of 8",
    "which_reps": [3, 4, 5, 6, 7, 8],
    "severity": "knee_valgus_distance 0.18–0.22",
    "valgus_phase": "LATE",
    "trend": "worsening +0.02/rep",
    "source": "both"
  },
  "excessive_forward_lean": {
    "present": false,
    "reps_affected": "0 of 8",
    "which_reps": [],
    "severity": "back_angle_max 38° — within range",
    "breakdown_timing": null,
    "trend": "stable",
    "source": "json"
  }
}
```

> `fault_detail.knee_valgus.reps_affected` and `which_reps` are the key signals Haiku Call 2 uses for longitudinal coaching — e.g. "valgus showing on rep 3 this session vs rep 5 last session — it's getting worse."

---

### Field Reference — Coaching Output *(Updated May 19 — new fields, old Nemotron fields removed)*

| Field | Type | Nullable | Written by | Step |
|---|---|---|---|---|
| `annotated_frame_url` | string (GCS URI) | **Yes** (NULL until Step 5b) | S2 — worst-rep annotated frame + gold standard comparison. *🆕 Added May 19 (moved from `form_analyses`, was array — now single URI)* | Step 5b UPDATE |
| `coaching_output` | jsonb | No | S2 — full Haiku Call 1 JSON. See structure below. *Updated May 19 — new flat per-parameter fields* | Step 5 INSERT |
| `progression_output` | jsonb | **Yes** (NULL until Haiku Call 2) | S2 — Section 1 (today vs previous) + Section 2 (5-session trend) for Tab 2. *🆕 Added May 19 — replaces `comparison_coaching_output`* | Async UPDATE |

**`coaching_output` JSONB structure** *(Updated May 19 — flat per-parameter fields replace old `parameters` block):*
```json
{
  "verdict": "2–4 sentence overall assessment. Leads with most important finding.",

  "posture_affirmation":          "What's working for posture",
  "posture_observation":          "What's off for posture — specific, references rep numbers",
  "posture_feedback":             "What to do — concrete drill or cue",

  "stability_affirmation":        "What's working for stability",
  "stability_observation":        "What's off for stability",
  "stability_feedback":           "What to do",

  "movement_quality_affirmation": "What's working for movement quality",
  "movement_quality_observation": "What's off for movement quality",
  "movement_quality_feedback":    "What to do",

  "range_of_motion_affirmation":  "What's working for range of motion",
  "range_of_motion_observation":  "What's off for range of motion",
  "range_of_motion_feedback":     "What to do",

  "next_session_focus": [
    "Actionable point 1 — drill name, rep/set target",
    "Actionable point 2",
    "Actionable point 3 (omit if only 2 genuinely matter)"
  ],

  "rep_trend": {
    "observation":    "How form evolved from rep 1 to last rep",
    "recommendation": "Single most important focus based on this trend"
  }
}
```

> `recommendation` field removed May 21 — replaced by `next_session_focus` array (2–3 specific actionable points rendered as a checklist on the Results screen).

```json
```

> **FE mapping:** Each parameter's 3 fields are read directly by field name — no array filtering needed. e.g. `coaching_output.posture_affirmation`, `coaching_output.posture_observation`, `coaching_output.posture_feedback`.

**`progression_output` JSONB structure:**
```json
{
  "section_1": {
    "today":    { "date": "2026-05-18", "weight_kg": 12, "overall_score": 79 },
    "previous": { "date": "2026-05-11", "weight_kg": 12, "overall_score": 72 },
    "overall_variance": 7,
    "overall_verdict": "string",
    "parameters": [
      { "name": "posture",          "variance": 5, "verdict": "string" },
      { "name": "stability",        "variance": 9, "verdict": "string" },
      { "name": "movement_quality", "variance": 6, "verdict": "string" },
      { "name": "range_of_motion",  "variance": 3, "verdict": "string" }
    ],
    "weight_decision": { "verdict": "hold | good_to_progress | drop_weight", "reasoning": "string" }
  },
  "section_2": {
    "insights": ["string (insight 1)", "string (insight 2)", "string (insight 3)"]
  }
}
```

> Rep-by-rep graph and 5-session progression graph are rendered by the frontend from `rep_scores` and session history queried from DB — not produced by Haiku Call 2.

---

### Removed fields (May 19, 2026)

| Field | Reason removed |
|---|---|
| `nemotron_output_url` | Haiku output stored directly in `coaching_output` JSONB — no GCS file needed |
| `chain_of_thought` | Replaced by `causal_chain` column (structured, not free text) |
| `annotated_frames_urls` (array) | Replaced by `annotated_frame_url` (single URI — one worst-rep image) |
| `issues_json` | Replaced by `fault_detail` column (Haiku format) |
| `progression_recommendation` (enum) | Moved to `progression_output.section_1.weight_decision.verdict` (Tab 2 only) |
| `session_tags` | Superseded by `issue_tags` + `faults_detected` |
| `comparison_coaching_output` | Renamed to `progression_output` |

---

### Roadmap tasks

| Task | Squad | Description |
|---|---|---|
| S2-W5-06 | S2 | Defines `form_analysis_results` DB schema |
| S2-W7-01 | S2 | Integrates Haiku Call 1 — single INSERT with all fields |
| S2-W7-05 | S2 | Assembles Haiku prompt and validates full output schema |
| PATCH-S2-W7-A | S2 | DB migration — add new columns, remove old Nemotron columns |
| S2-W8-01 | S2 | Progression logic — weight decision inside `progression_output.section_1.weight_decision` |

---

## 3. `exercises`

**Purpose:** Seed / reference table. Static list of supported exercises. All squads reference `exercise_id` — never change once set.
**One row per:** Supported exercise
**PK:** `exercise_id`
**Write timing:** Manual seed — populated in W5 before upload endpoints are built.

### Field Reference

| Field | Type | Nullable | Format | Notes |
|---|---|---|---|---|
| `exercise_id` | uuid (PK) | No | e.g. `ex_gob_squat_001` | Cross-squad identifier. **Never change once set.** |
| `exercise_slug` | string (unique) | No | snake_case e.g. `goblet_squat` | Used by backend routing and ML pipeline. **Never change once set.** |
| `display_name` | string | No | Title case e.g. `Goblet Squat` | Rendered on frontend — exercise picker, results screen, history. |
| `category` | string | No | e.g. `strength` | Used for exercise picker filtering. |
| `muscle_groups` | jsonb array | No | `["quads", "glutes", "core"]` | Primary muscles. |
| `form_image_url` | string (GCS URI) | **Yes** | `gs://kinetic-assets/exercises/{slug}/form_reference.jpg` | Static reference image shown before upload. |
| `form_video_url` | string (GCS URI) | **Yes** | `gs://kinetic-assets/exercises/{slug}/form_reference.mp4` | Optional demo video. |
| `form_tips` | jsonb array | No | `["Keep chest tall...", ...]` | Key form cues shown as checklist before upload. |
| `camera_angle_tips` | jsonb array | No | max 5 items | Filming guidance — shown on upload screen. |
| `is_active` | boolean | No | `true` \| `false` | Controls exercise picker visibility. MVP: Goblet Squat = `true`. |

**MVP seed data:**

| exercise_id | exercise_slug | display_name | is_active |
|---|---|---|---|
| `ex_gob_squat_001` | `goblet_squat` | Goblet Squat | `true` |

---

## 4. `gold_standard_biomechanics`

**Purpose:** Reference data for elite-form Goblet Squat. 2–5 reference videos processed through MediaPipe + biomechanics script. Used by: (1) Haiku Call 1 prompt — gold standard JSON passed directly for angle comparison, (2) OpenCV Part 2 — `joint_angle_ranges` used for annotation overlay showing user angles vs ideal.
**One row per:** Reference video processed
**Write timing:** Manual — W7 data prep (S3-W7-02). Must be ready before Haiku Call 1 prompt work begins.

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `id` | uuid (PK) | No | Reference entry ID |
| `exercise_id` | uuid (FK → exercises) | No | MVP: always `ex_gob_squat_001` |
| `label` | string | No | e.g. `"reference_01"` — identifies the source video |
| `biomechanics_json` | jsonb | No | Full MediaPipe + biomechanics script output. Same schema as user session output — passed directly into Haiku Call 1 prompt. |
| `joint_angle_ranges` | jsonb | No | Min/max angle ranges per joint. Used by OpenCV Part 2 for annotation overlay — gold standard comparison text drawn alongside user's actual angles. |
| `created_at` | timestamp | No | When this reference was processed |

---

## Cross-Table Relationships

```
exercises
  └─ exercise_id (PK)
       ├─ form_analyses.exercise_id (FK)
       └─ form_analysis_results.exercise_id (FK)

form_analyses
  └─ analysis_id (PK)
       └─ form_analysis_results.analysis_id (FK / same PK)

form_analyses
  └─ session_id
       └─ form_analysis_results.session_id (FK → form_analyses.session_id)

gold_standard_biomechanics
  └─ exercise_id (FK → exercises)
       (used at query time by Haiku Call 1 prompt + OpenCV Part 2 — no FK to analysis tables)
```

**Haiku Call 2 — last 5 sessions query:**
```sql
SELECT
  analysis_id, weight_value, weight_unit, weight_kg_normalised,
  overall_form_score, posture_score, stability_score,
  movement_quality_score, range_of_motion_score,
  rep_scores, fault_detail, coaching_output, created_at
FROM form_analysis_results
WHERE exercise_id = [current exercise_id]
  AND user_id     = [current user_id]
  AND analysis_id != [current analysis_id]
  AND coaching_output IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;
```

---

## Changelog
- May 21, 2026: Haiku output schema updates.
  - `confidence` renamed → `fault_confidence` (fault detection certainty)
  - `causal_chain` (object) renamed → `causal_chains` (jsonb array — supports multiple independent root causes)
  - Added to each `causal_chains` entry: `causal_confidence`, `confidence_note`, `affected_parameters`
  - `recommendation` removed from `coaching_output` → replaced by `next_session_focus` array
  - Added `camera_angle` flat column — echoed from biomechanics JSON, required for OpenCV gold standard matching
  - Added `reasoning` column — Haiku chain-of-thought stored for debugging
- May 19, 2026: Full architecture update — Nemotron → Haiku 4.5.
  - Write pattern: Phase 1/2 Nemotron/Claude → single INSERT on Haiku Call 1
  - Removed: `nemotron_output_url`, `chain_of_thought`, `annotated_frames_urls`, `issues_json`, `progression_recommendation`, `session_tags`, `comparison_coaching_output`
  - Renamed: `tempo_score` → `range_of_motion_score`
  - Added: `range_of_motion_score`, `rep_scores` (updated format), `faults_detected`, `confidence`, `causal_chain`, `fault_detail`, `trends`, `annotated_frame_url` (single URI), `progression_output`
  - `coaching_output` JSONB: replaced `parameters` block with flat per-parameter fields: `{parameter}_affirmation`, `{parameter}_observation`, `{parameter}_feedback` for all 4 parameters
  - Comparison query updated: `progression_recommendation IS NOT NULL` → `coaching_output IS NOT NULL`, LIMIT 5
- May 12, 2026: Initial creation.
