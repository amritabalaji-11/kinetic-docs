# Kinetic — Database Schema
**Last updated:** May 12, 2026  
**Scope:** All DB tables · field types · write timing · squad ownership  
**Owner:** S2 — Backend defines and owns all DB schemas  
**Related docs:** `FE_Response_Schemas.md` · `FE_SSE_and_Errors.md` · `technical_data_schema.html`

---

## Tables at a Glance

| Table | Type | Rows created | Written by |
|---|---|---|---|
| `form_analyses` | Job record | One per video upload | S2 — 3-step write pattern |
| `form_analysis_results` | AI output record | One per completed analysis | S2 — 2-phase write pattern |
| `exercises` | Seed / reference | One per supported exercise | Manual seed — agreed cross-squad |
| `gold_standard_biomechanics` | Reference data | 3–5 per exercise | Manual — W6 data prep |

---

## Write Pattern Overview

Each table has multiple write moments across the pipeline. This is the full map:

| Pipeline step | What happens | Table written | Write type |
|---|---|---|---|
| **Step 2** — Upload | Video stored to GCS | `form_analyses` | INSERT (initial, most fields) |
| **Step 3** — MediaPipe → Quality Gate | S3 returns keypoints + quality check | `form_analyses` | UPDATE (`quality_gate_status`, `video_score`) |
| **Step 5** — Nemotron complete | S3 returns scored output | `form_analysis_results` | INSERT Phase 1 (scores + issues; coaching fields NULL) |
| **Step 5b** — OpenCV frame extraction | S2 extracts annotated frame | `form_analyses` | UPDATE (`annotated_frame_url`) |
| **Step 7** — Claude complete | S2 writes coaching output | `form_analysis_results` | UPDATE Phase 2 (`coaching_output`, `progression_recommendation`, `session_tags`) |
| **Step 7** — Pipeline complete | S2 marks job done | `form_analyses` | UPDATE (`status = complete`) |
| **Async after Step 7** — Comparison | S2 runs second Claude call | `form_analysis_results` | UPDATE (`comparison_coaching_output`) |

> **Why two tables?** `form_analyses` is the job record — it exists from the moment of upload, even if the pipeline fails. `form_analysis_results` is the output record — it only exists once Nemotron completes. A failed analysis leaves a `form_analyses` row with `status = failed` but no `form_analysis_results` row. This makes failure states easy to query and retry logic clean.

---

## 1. `form_analyses`

**Purpose:** Primary upload record. Created at upload. Tracks pipeline status. Updated as each pipeline stage completes.  
**One row per:** Video upload  
**PK:** `analysis_id`

### Write pattern

```
Step 2 — Upload
  INSERT: all fields except quality_gate_status, video_score, annotated_frame_url (all NULL)

Step 3 — Quality gate result received from S3
  UPDATE: quality_gate_status, video_score
  (if quality gate fails → status = failed, no further writes)

Step 5b — OpenCV frame extraction complete
  UPDATE: annotated_frame_url

Step 7 — Claude complete / pipeline done
  UPDATE: status = complete
```

### Field Reference

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `analysis_id` | uuid (PK) | No | 36 chars | — | S2 — `uuid4()` at upload handler | Step 2 — INSERT |
| `session_id` | uuid | No | 36 chars | — | S1 → sent in POST body from sessionStorage | Step 2 — INSERT |
| `user_id` | uuid | No | 36 chars | — | S1 → hardcoded in frontend (one of `user_001`, `user_002`, `user_003`) · sent in POST body · pre-seeded in DB. Auth de-scoped. | Step 2 — INSERT |
| `exercise_id` | uuid (FK → exercises) | No | — | — | S1 → sent in POST body | Step 2 — INSERT |
| `weight_value` | float | No | 0.5 – 999.9 | 1 dp | S1 → sent in POST body | Step 2 — INSERT |
| `weight_unit` | enum | No | `kg` \| `lb` | — | S1 → sent in POST body | Step 2 — INSERT |
| `weight_kg_normalised` | float | No | 0.5 – 999.9 | 4 dp | S2 — computed at upload. If `lb`: value × 0.453592. If `kg`: value as-is. | Step 2 — INSERT |
| `video_url` | string (GCS URI) | No | — | `gs://kinetic-videos/videos/{user_id}/{analysis_id}/original.mp4` | S2 — constructed after GCS upload | Step 2 — INSERT |
| `created_at` | timestamp | No | — | ISO 8601 UTC | S2 — server time at upload receipt | Step 2 — INSERT |
| `status` | enum | No | `uploaded` \| `processing` \| `complete` \| `failed` | — | S2 — `uploaded` at INSERT, `processing` when pipeline starts, `complete` at Step 7, `failed` on terminal error | Step 2 INSERT → updated Step 7 |
| `quality_gate_status` | enum | **Yes** (NULL until Step 3) | `GOOD` \| `ACCEPTABLE` | — | S2 — written after receiving quality gate result from S3. Passed to LLM context to calibrate confidence. | Step 3 UPDATE — quality gate result |
| `video_score` | numeric(4,3) | **Yes** (NULL until Step 3) | 0.000 – 1.000 | 3 dp | S2 — composite visibility score from Landmark Quality Framework Layer 2. Written in same UPDATE as `quality_gate_status`. | Step 3 UPDATE — quality gate result |
| `annotated_frame_url` | string (GCS URI) | **Yes** (NULL until Step 5b) · V2 | — | `gs://kinetic-videos/analyses/{analysis_id}/frame_bottom.jpg` | S2 — GCS URI of worst-rep bottom frame with joint angle overlay. Written after OpenCV extraction. Worst rep = lowest overall score. | Step 5b UPDATE — OpenCV extraction complete |

**V2 note:** `quality_gate_status`, `video_score`, and `annotated_frame_url` were added May 8–9, 2026. All are nullable — NULL is a valid state meaning "not yet run". Query as `IS NULL` to find analyses awaiting these steps.

**Roadmap tasks:**

| Task | Squad | Description |
|---|---|---|
| S2-W5-06 | S2 | Defines `form_analyses` DB schema |
| S2-W6-01 | S2 | Upload endpoint — INSERT initial row, generate `analysis_id`, open SSE stream |
| S2-W6-05 | S2 | Quality gate integration — UPDATE `quality_gate_status` + `video_score` |
| S2-W7-02 | S2 | OpenCV frame extraction — UPDATE `annotated_frame_url` |

---

## 2. `form_analysis_results`

**Purpose:** AI pipeline output. Created when Nemotron completes (Phase 1). Updated when Claude completes (Phase 2). Updated again asynchronously with comparison coaching output.  
**One row per:** Completed analysis  
**PK:** `analysis_id` (same ID as `form_analyses`)

### Write pattern

```
Step 5 — Nemotron complete (Phase 1 INSERT)
  INSERT: identity fields + weight fields + scores + issues + nemotron output
  coaching_output = NULL
  progression_recommendation = NULL
  session_tags = NULL
  comparison_coaching_output = NULL

Step 7 — Claude complete (Phase 2 UPDATE)
  UPDATE WHERE analysis_id = [current]:
    coaching_output = <Claude JSON>
    progression_recommendation = hold | progress | drop
    session_tags = ["tag1", "tag2"]

Async after Step 7 — Comparison coaching (async UPDATE)
  UPDATE WHERE analysis_id = [current]:
    comparison_coaching_output = <Claude comparison JSON>
  (only runs if a previous completed analysis exists for same exercise_id + user_id)
```

### Field Reference — Identity & Weight (written Phase 1)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `analysis_id` | uuid (PK) | No | 36 chars | — | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `session_id` | uuid (FK → form_analyses) | No | 36 chars | — | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `user_id` | uuid | No | 36 chars | — | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `exercise_id` | uuid (FK → exercises) | No | — | — | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `weight_value` | float | No | 0.5 – 999.9 | 1 dp | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `weight_unit` | enum | No | `kg` \| `lb` | — | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |
| `weight_kg_normalised` | float | No | 0.5 – 999.9 | 4 dp | S2 — copied from `form_analyses` | Step 5 — Phase 1 INSERT |

### Field Reference — Session-level Scores (written Phase 1)

These are averaged across all reps. Stored as flat columns for fast querying in progression logic and comparison.

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `overall_form_score` | integer | No | 0 – 100 | — | S2 — from Nemotron output. Serialised as `overall_score` in API responses. | Step 5 — Phase 1 INSERT |
| `posture_score` | integer | No | 0 – 100 | — | S2 — from Nemotron output | Step 5 — Phase 1 INSERT |
| `stability_score` | integer | No | 0 – 100 | — | S2 — from Nemotron output | Step 5 — Phase 1 INSERT |
| `movement_quality_score` | integer | No | 0 – 100 | — | S2 — from Nemotron output | Step 5 — Phase 1 INSERT |
| `tempo_score` | integer | No | 0 – 100 | — | S2 — from Nemotron output. Required as flat column so comparison query can retrieve previous session tempo without parsing JSONB. | Step 5 — Phase 1 INSERT |

> All 5 score columns are stored flat for direct queryability in progression logic and the comparison endpoint. Tempo is also present inside `coaching_output` JSONB (Phase 2) as part of the full parameter block.

### Field Reference — Rep-level Scores (written Phase 1)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `rep_count` | integer | No | 1 – 99 | — | S2 — from Nemotron output | Step 5 — Phase 1 INSERT |
| `rep_scores` | jsonb array | No | each score: 0–100 | `[{ "rep_number": 1, "form_score": 74, "movement_quality_score": 70, "stability_score": 78, "posture_score": 72 }, ...]` · API comparison response serialises as integer array of `form_score` values only: `[74, 68, ...]` | S2 — from Nemotron output | Step 5 — Phase 1 INSERT |

### Field Reference — Issues (written Phase 1)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `issue_tags` | text[] + GIN index | No | — | `["knee_valgus", "ankle_dorsiflexion"]` | S2 — extracted from `issues_json[].type` at write time. Stored flat for fast filtering. | Step 5 — Phase 1 INSERT |
| `issues_json` | jsonb | No | — | `[{ "issue_id": "issue_001", "type": "knee_valgus", "severity": "moderate", "reps_affected": [3, 4], "key_frames": [...] }]` | S2 — full Nemotron issue output | Step 5 — Phase 1 INSERT |

**Issue tag vocabulary (fixed set):** `knee_valgus` · `ankle_dorsiflexion` · `depth` · `torso_lean` · `hip_hinge`

GIN index query examples:
- `WHERE 'knee_valgus' = ANY(issue_tags)` — single tag filter
- `WHERE issue_tags @> ARRAY['knee_valgus','depth']` — multiple tag filter

### Field Reference — Nemotron Outputs (written Phase 1)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `nemotron_output_url` | string (GCS URI) | No | — | `gs://kinetic-videos/videos/{user_id}/{analysis_id}/nemotron_out.json` | S2 — full Nemotron output JSON stored in GCS | Step 5 — Phase 1 INSERT |
| `annotated_frames_urls` | jsonb array (GCS URIs) | No | — | `["gs://kinetic-videos/.../frames/annotated/f_001.jpg"]` | S2 — per-issue annotated frame URLs from OpenCV | Step 5 — Phase 1 INSERT |
| `chain_of_thought` | text | No | max ~2000 chars | — | S2 — Nemotron chain-of-thought paragraph. Used as context for Claude. Not shown directly on frontend. | Step 5 — Phase 1 INSERT |

### Field Reference — Claude Outputs (NULL at Phase 1 · written Phase 2)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `coaching_output` | jsonb | **Yes** (NULL at Phase 1) | — | See structure below | S2 — Claude Sonnet output | Step 7 — Phase 2 UPDATE |
| `progression_recommendation` | enum | **Yes** (NULL at Phase 1) | `hold` \| `progress` \| `drop` | — | S2 — from Claude Sonnet. Determines weight progression advice. | Step 7 — Phase 2 UPDATE |
| `session_tags` | text[] | **Yes** (NULL at Phase 1) | — | `["knee_valgus", "fatigue_pattern"]` | S2 — Claude-generated session-level tags (broader than `issue_tags`) | Step 7 — Phase 2 UPDATE |

**`coaching_output` JSONB structure:**
```json
{
  "summary_paragraph": "string (max ~400 chars)",
  "parameters": {
    "posture":          { "score": 68, "affirmation": null, "observation": null, "correction": "string" },
    "stability":        { "score": 80, "affirmation": null, "observation": null, "correction": "string" },
    "movement_quality": { "score": 85, "affirmation": null, "observation": null, "correction": "string" },
    "tempo":            { "score": 55, "affirmation": null, "observation": null, "correction": "string" }
  }
}
```
> `affirmation` and `observation` are null in W6/W7 — reserved for W8 design iteration.

### Field Reference — Comparison Coaching (NULL until async step)

| Field | Type | Nullable | Range / Max | Format | Written by | Pipeline step |
|---|---|---|---|---|---|---|
| `comparison_coaching_output` | jsonb | **Yes** (NULL until async step) | — | See structure below | S2 — second Claude call, async after `analysis_complete` SSE fires. Only populated if a previous completed analysis exists for same `exercise_id` + `user_id`. | Async after Step 7 |

**`comparison_coaching_output` JSONB structure:**
```json
{
  "summary_paragraph": "string (max ~400 chars)",
  "parameters": {
    "posture":          { "observation_action": "string (max ~300 chars)" },
    "stability":        { "observation_action": "string" },
    "movement_quality": { "observation_action": "string" },
    "tempo":            { "observation_action": "string" }
  }
}
```

**Roadmap tasks:**

| Task | Squad | Description |
|---|---|---|
| S2-W5-06 | S2 | Defines `form_analysis_results` DB schema — all fields |
| S2-W7-01 | S2 | Saves Nemotron output — Phase 1 INSERT |
| S2-W7-04 | S2 | After Claude step — Phase 2 UPDATE (`coaching_output`, `progression_recommendation`) |
| S2-W8-01 | S2 | Progression recommendation logic — determines `hold` / `progress` / `drop` |

---

## 3. `exercises`

**Purpose:** Seed / reference table. Static list of exercises the app supports. All squads reference `exercise_id` — it is the cross-squad agreed identifier. New exercises must be added here and `exercise_id` confirmed across squads before any backend or frontend work begins.  
**One row per:** Supported exercise  
**PK:** `exercise_id`  
**Write timing:** Manual seed — populated in W5 by S2 before any upload endpoints are built.

### Field Reference

| Field | Type | Nullable | Range / Max | Format | Notes |
|---|---|---|---|---|---|
| `exercise_id` | uuid (PK) | No | 36 chars | e.g. `ex_gob_squat_001` | Stable cross-squad ID. Referenced by `form_analyses` and `form_analysis_results`. **Never change once set.** |
| `exercise_slug` | string (unique) | No | max 50 chars | snake_case e.g. `goblet_squat` | Used by backend routing and ML pipeline. **Never change once set.** |
| `display_name` | string | No | max 100 chars | Title case e.g. `Goblet Squat` | Rendered on frontend — exercise picker, results screen, history. |
| `category` | string | No | max 50 chars | e.g. `strength` · `mobility` · `cardio` | Used for exercise picker filtering. |
| `muscle_groups` | jsonb array | No | — | `["quads", "glutes", "core"]` | Primary muscles. Shown on exercise detail screen. |
| `form_image_url` | string (GCS URI) | **Yes** | — | `gs://kinetic-assets/exercises/{slug}/form_reference.jpg` | Static reference image of correct form. Shown on exercise detail + upload guidance screen. **Must be populated before S1-W6-02.** |
| `form_video_url` | string (GCS URI) | **Yes** | — | `gs://kinetic-assets/exercises/{slug}/form_reference.mp4` | Short demo video. Optional — shown alongside `form_image_url` if available. |
| `form_tips` | jsonb array | No | max 10 items · each max 150 chars | `["Keep chest tall throughout the movement", ...]` | Ordered key form cues. Rendered as a checklist before upload. |
| `camera_angle_tips` | jsonb array | No | max 5 items · each max 200 chars | `["Film from the side (sagittal view) — camera at hip height", ...]` | Shown on upload screen before filming. Critical for video quality and ML accuracy. |
| `is_active` | boolean | No | — | `true` \| `false` | `false` = not yet live. Controls exercise picker visibility. MVP: Goblet Squat is `true`. |

**MVP seed data:**

| exercise_id | exercise_slug | display_name | is_active | Must be ready before |
|---|---|---|---|---|
| `ex_gob_squat_001` | `goblet_squat` | Goblet Squat | `true` | S1-W6-02 (Upload screen build) |

---

## 4. `gold_standard_biomechanics`

**Purpose:** Reference data for good-form Goblet Squat. 3–5 reference videos processed through MediaPipe + biomechanics script. Used by (1) OpenCV Part 2 overlay as gold standard angle ranges for visual comparison, and (2) Claude system prompt as reference values for coaching context.  
**One row per:** Reference video processed  
**Write timing:** Manual — W6 data prep, before OpenCV overlay and Claude prompt work begins.

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `id` | uuid (PK) | No | Reference entry ID |
| `exercise_id` | uuid (FK → exercises) | No | MVP: always `ex_gob_squat_001` |
| `label` | string | No | e.g. `"reference_01"` — identifies the source video |
| `biomechanics_json` | jsonb | No | Full MediaPipe + biomechanics script output for this reference video |
| `joint_angle_ranges` | jsonb | No | Min/max angle ranges per joint derived from this reference. Used by OpenCV overlay. |
| `created_at` | timestamp | No | When this reference was processed |

> Full field spec to be confirmed with S3 at W6 data prep. Schema above is provisional — S3 owns the definition.

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
       (used at query time by Claude prompt + OpenCV — no FK to analysis tables)
```

**Comparison query (no FK stored):**
```sql
SELECT * FROM form_analysis_results
WHERE exercise_id = [current exercise_id]
  AND user_id = [current user_id]
  AND analysis_id != [current analysis_id]
  AND progression_recommendation IS NOT NULL
ORDER BY created_at DESC
LIMIT 1;
```
The "previous session" for comparison is resolved at query time — not stored as a foreign key.

---

## Changelog
- May 12, 2026: Initial creation — consolidated all DB table definitions from `technical_data_schema.html` and `FE_Response_Schemas.md`. Full field reference with types, nullable, format, write timing, and squad ownership for all 4 tables.
