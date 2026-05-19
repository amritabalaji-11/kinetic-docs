# Kinetic — SSE Events, Error Codes & Frontend Messages
**Last updated:** May 19, 2026 *(architecture update: Nemotron → Haiku 4.5, Tab 1/Tab 2 model)*
**Scope:** SSE event shapes · Error taxonomy · HTTP error codes · Frontend UI copy
**Produced by:** S2 — Backend
**Consumed by:** S1 — Frontend

---

## How SSE Works in Kinetic

**Two separate connections — Option B (confirmed):**

1. `POST /upload` returns `{"analysis_id": "uuid"}` as normal JSON immediately — no streaming, closes right away.
2. S1 opens a separate `EventSource` at `GET /analysis/{analysis_id}/stream` to receive live pipeline events.

*(Updated May 19, 2026 — sequence diagram rewritten for Haiku 4.5 architecture)*

```
Frontend (S1)                     Backend (S2)                    Data/CV (S3)
   |                                 |                                 |
   |--- POST /upload --------------> |                                 |
   |<-- { "analysis_id": "uuid" } -- |  ← JSON, closes immediately    |
   |                                 |                                 |
   |--- GET /analysis/{id}/stream -> |                                 |
   |<-- SSE stream opens ----------- |                                 |
   |<-- upload_received ------------ |                                 |
   |                                 |--- dispatch MediaPipe job ----> |
   |<-- mediapipe_started ---------- |                                 |
   |                                 |<-- keypoints returned --------- |
   |<-- mediapipe_complete --------- |                                 |
   |                                 |<-- biomechanics JSON returned - |
   |<-- biomechanics_complete ------ | (silent — % bar only)          |
   |                                 |--- call Haiku Call 1 ---------> |
   |<-- haiku_started -------------- |                                 |
   |                                 |<-- coaching JSON returned ----- |
   |<-- analysis_ready ------------- |  ← Tab 1 unlocks               |
   |                                 |                                 |
   |--- GET /analysis/{id}/result -> |  ← S1 fetches full results     |
   |<-- full coaching response ------ |                                |
   |                                 |                                 |
   | [Tab 1 visible, user reading]   |                                 |
   |                                 |--- OpenCV Part 2 runs --------> |
   |                                 |<-- annotated_frame_url -------- |
   |<-- frame_ready ---------------- |  ← image swaps in Tab 1        |
   |                                 |                                 |
   | [async — Tab 2 loading state]   |                                 |
   |                                 |--- call Haiku Call 2 (async) -> |
   |                                 |<-- progression JSON returned -- |
   |<-- progression_ready ---------- |  ← Tab 2 unlocks               |
   |                                 |                                 |
   |--- GET /analysis/{id}/progression|  ← S1 fetches Tab 2 data     |
   |<-- Section 1 + Section 2 ------- |                               |
```

> The stream stays open after `analysis_ready` to receive `frame_ready` and `progression_ready`. It may be closed after `progression_ready` fires or after a timeout.

---

## Squad Dependencies Overview

*(Updated May 19, 2026 — removed Nemotron/RAG/Claude events, added Haiku events)*

| Event | Fired by | Consumed by | Inter-squad dependency |
|---|---|---|---|
| `upload_received` | S2 | S1 | S1 POST triggers S2 |
| `mediapipe_started` | S2 | S1 | S2 dispatches job to S3 — **S3 must be ready to accept jobs** |
| `mediapipe_complete` | S2 | S1 | **S3 must return keypoints to S2** before S2 can fire this |
| `biomechanics_complete` | S2 | S1 | **S3 must return biomechanics JSON to S2** before S2 can fire this |
| `haiku_started` | S2 | S1 | S2-internal — no S3 dependency |
| `analysis_ready` | S2 | S1 | Haiku Call 1 must complete + all scores written to DB |
| `frame_ready` | S2 | S1 | **S3 must run OpenCV Part 2 and return annotated_frame_url** before S2 fires this |
| `progression_ready` | S2 | S1 | Haiku Call 2 must complete + progression_output written to DB — async |
| `error` | S2 (pipeline) or S1 (pre-upload) | S1 | Stage-dependent — see error taxonomy |

**S2 ↔ S3 output format dependency:**
S2 fires `mediapipe_complete` and `biomechanics_complete` using data returned by S3. S2 fires `frame_ready` when S3 returns `annotated_frame_url`. S2 must not hardcode field assumptions — S3 output schemas defined in `Kinetic_Biomechanics_Output_Schema.json` are the contract.

---

## Common Fields — Every SSE Event

Every event (including `error`) always carries these three fields:

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `analysis_id` | uuid | No | The ID issued at upload. Use this to match events to the correct upload if multiple tabs are open. |
| `session_id` | uuid | No | Browser-visit UUID from sessionStorage. Echoed back — frontend can use to verify event belongs to current session. |
| `user_id` | uuid | No | Device-level ID from localStorage. Echoed back. |

---

## 1. Pipeline SSE Events

*(Updated May 19, 2026 — events rewritten for Haiku architecture)*

### `upload_received`
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** None

Fires immediately after S2 receives and stores the video to GCS and writes the initial `form_analyses` row.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "filename":    "squat_session.mp4",
  "size_mb":     43.12,
  "created_at":  "2026-05-06T10:23:00.412Z"
}
```

| Field | Type | Nullable | FE Note |
|---|---|---|---|
| `filename` | string | No | Original filename. Display on processing screen if helpful. |
| `size_mb` | float | No | Internal reference. Not required to display. |
| `created_at` | timestamp | No | ISO 8601 UTC. Used later in results — not displayed during processing. |

**Suggested UI copy:** "Video received. Preparing your session..."

---

### `mediapipe_started`
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** S2 dispatches MediaPipe job to S3 immediately before firing

Fires when S2 dispatches the pose detection job to S3.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "video_url":   "gs://kinetic-videos/videos/{user_id}/{analysis_id}/original.mp4"
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `video_url` | string (GCS URI) | No | Internal reference passed to S3. Do not display or link — GCS URIs are not public URLs. |

**Suggested UI copy:** "Reading your movement patterns..."

---

### `mediapipe_complete`
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** S3 must return keypoints to S2 before S2 fires this

Fires when S3 returns MediaPipe keypoints to S2.

```json
{
  "analysis_id":        "uuid",
  "session_id":         "uuid",
  "user_id":            "uuid",
  "rep_count":          8,
  "fps":                30,
  "keypoints_detected": 33,
  "frames_processed":   1356
}
```

| Field | Type | Nullable | FE Note |
|---|---|---|---|
| `rep_count` | integer | No | Can surface as "X reps detected" on processing screen. |
| `fps` | integer | No | Internal. Not required to display. |
| `keypoints_detected` | integer | No | Internal. Not required to display. |
| `frames_processed` | integer | No | Internal. Not required to display. |

**Suggested UI copy:** "Movement detected — {rep_count} reps found"

---

### `biomechanics_complete`
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** S3 must return biomechanics JSON to S2 before S2 fires this

Silent event — % bar advances only. No user-facing message change. Fires after S3 returns the joint angle and biomechanics output.

```json
{
  "analysis_id":     "uuid",
  "session_id":      "uuid",
  "user_id":         "uuid",
  "rep_count":       8,
  "joints_computed": 6,
  "avg_confidence":  0.87
}
```

| Field | Type | Nullable | FE Note |
|---|---|---|---|
| `rep_count` | integer | No | Confirms rep count consistency. Internal. |
| `joints_computed` | integer | No | Internal. Not required to display. |
| `avg_confidence` | float | No | Internal. Not required to display. |

**Suggested UI copy:** No message change — % bar nudges only.

---

### `haiku_started` *(Added May 19, 2026)*
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** None — S2 calls Anthropic API internally

Fires when S2 begins the Haiku Call 1 API request (form analysis + coaching in one call).

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Suggested UI copy:** "Analysing your form frame by frame..."

---

### `analysis_ready` *(Added May 19, 2026 — replaces `analysis_complete`)*
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** None — fires after Haiku Call 1 completes and all scores + coaching_output are written to DB

**Tab 1 unlocks on this event.** S1 fetches full results via `GET /analysis/{id}/result`.

```json
{
  "analysis_id":   "uuid",
  "session_id":    "uuid",
  "user_id":       "uuid",
  "overall_score": 72
}
```

| Field | Type | Nullable | FE Note |
|---|---|---|---|
| `overall_score` | integer | No | Overall form score 0–100. Can preview on processing screen as it transitions to results. |

**Frontend action on receipt:** Navigate to Results screen (Tab 1). Call `GET /analysis/{id}/result` to load full coaching data.

---

### `frame_ready` *(Added May 19, 2026 — replaces `frames_extracting` + `frames_ready`)*
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** S3 runs OpenCV Part 2 and returns annotated_frame_url before S2 fires this

Fires ~2–3 seconds after `analysis_ready`. Tab 1 coaching text is already visible. Image placeholder swaps to annotated frame.

```json
{
  "analysis_id":         "uuid",
  "session_id":          "uuid",
  "user_id":             "uuid",
  "annotated_frame_url": "https://storage.googleapis.com/kinetic-videos/analyses/{analysis_id}/worst_rep_frame.jpg"
}
```

| Field | Type | Nullable | FE Note |
|---|---|---|---|
| `annotated_frame_url` | string (URL) | No | Public signed URL. Use directly as `<img src>`. No separate API call needed. |

**Frontend action on receipt:** Swap image placeholder with annotated frame in Tab 1.

---

### `progression_ready` *(Added May 19, 2026 — replaces `comparison_ready`)*
**Fired by:** S2 — Backend · **Consumed by:** S1 — Frontend · **S3 dependency:** None — S2 runs Haiku Call 2 async after `analysis_ready`

Fires asynchronously after `analysis_ready`. Tab 1 is already fully visible. Tab 2 (User Progression) unlocks on this event.

Only fires if a previous completed analysis exists for the same `exercise_id` + `user_id`.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Frontend action on receipt:** Unlock Tab 2. Call `GET /analysis/{id}/progression` to load Section 1 (today vs previous) + Section 2 (5-session trend).

**If tab is opened before event fires:** Show a loading state — Tab 2 is visible but locked.

**If no previous session exists:** `progression_ready` fires with `NO_PREVIOUS_SESSION` error instead — Tab 2 shows empty state message.

---

## 2. Error SSE Event

**Fired by:** S2 — Backend (all pipeline stages) or S1 — Frontend (pre-upload validation only) · **Consumed by:** S1 — Frontend

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "error_code":  "KEYPOINTS_OCCLUDED",
  "error_stage": "quality_gate",
  "retryable":   "false",
  "message":     "MediaPipe confidence below threshold: 0.31"
}
```

**Field Reference** *(Updated May 19, 2026 — error_stage enum updated)*

| Field | Type | Nullable | Values | FE Note |
|---|---|---|---|---|
| `error_code` | enum (string) | No | See taxonomy below | Use this to look up user-facing copy. SCREAMING_SNAKE_CASE. |
| `error_stage` | enum (string) | No | `quality_gate` · `biomechanics` · `haiku_call_1` · `opencv_part_2` · `haiku_call_2` · `pipeline` | Identifies which pipeline stage failed. *(Updated May 19 — removed `nemotron`, `frame_extraction`, `rag`, `claude`)* |
| `retryable` | enum (string) | No | `"true"` · `"false"` · `"partial"` | **String, not boolean.** Use `retryable === "true"`. Never check truthiness — `"false"` is truthy in JS. |
| `message` | string | No | max 500 chars | **Internal log — never show to user.** Frontend derives copy from `error_code`. |

**CTA logic based on `retryable`:**

| Value | Meaning | Frontend action |
|---|---|---|
| `"true"` | Infra failure — same video is fine | Show **"Try again"** button. Re-submit same upload. |
| `"false"` | Video itself must change | Show **"Re-film and upload"** button. Navigate back to upload screen. |
| `"partial"` | Pipeline degraded but continues | Show **inline warning** — no blocking CTA. Results still load. |

---

## 3. Error Code Taxonomy

### Pre-upload — S1 validates client-side · never reaches SSE

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FILE_TOO_LARGE` | > 500 MB | "That video is too large (max 500 MB). Try trimming it to your working set." | `"false"` |
| `FORMAT_UNSUPPORTED` | Not `.mp4` / `.mov` / `.avi` | "We can't read that format. Export as MP4 and try again." | `"false"` |
| `FILE_CORRUPT` | Zero bytes or unreadable header | "That file looks corrupted. Re-export from your camera roll and try again." | `"false"` |
| `UPLOAD_TIMEOUT` | Network drop mid-transfer | "Upload timed out. Check your connection and try again." | `"true"` |

---

### Quality Gate — `error_stage: "quality_gate"`

**Owner: S3 evaluates · S2 fires the error event.**
Fires before any AI processing. If rejected here, no Haiku calls are made. All quality gate errors: `retryable: "false"`.

> **`landmark_medians` field:** For `occlusion_*` and `out_of_frame_*` codes, the error payload also includes a `landmark_medians` object with `median_visibility` and `median_presence` per critical landmark (knee/hip/heel, both sides). Used to confirm left/right message variant.

| error_code | Gate | Trigger condition | User-facing message | retryable |
|---|---|---|---|---|
| `occlusion_left_side` | M1 | ≥1 of knee/hip/heel on left side visibility ≤ 0.60. Right passes. | "Part of your left side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_right_side` | M1 | ≥1 of knee/hip/heel on right side visibility ≤ 0.60. Left passes. | "Part of your right side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_both_sides` | M2 | ≥1 of knee/hip/heel visibility ≤ 0.60 on both sides. | "We couldn't see your lower body clearly. Try angling your camera slightly toward the front so both legs are fully in view." | `"false"` |
| `out_of_frame_left` | M3 | Visibility passes but ≥1 of knee/hip/heel on left side median_presence ≤ 0.50. | "Your left side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `out_of_frame_right` | M3 | Visibility passes but ≥1 of knee/hip/heel on right side median_presence ≤ 0.50. | "Your right side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `poor_video_quality` | M4 | `video_score` < 0.70. Typical: filming from behind, obstruction, low lighting. | "We couldn't read your body position clearly. Film from your side with good lighting and a clear background." | `"false"` |
| `no_reps_detected` | M5 | `complete_reps` = 0. | "We couldn't detect any squats in your video. Make sure you're doing goblet squats and your full body is in frame from the start." | `"false"` |
| `insufficient_reps` | M6 | 0 < `complete_reps` < 3. | "Film a full set to get your analysis. We need at least 3 complete reps — squat all the way down and all the way back up for each one." | `"false"` |

---

### Biomechanics — `error_stage: "biomechanics"`

**Owner: S3 runs the script · S2 fires the error event.**

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `VIDEO_TOO_SHORT` | Video < 5s | "We didn't catch a complete rep. Record at least one full squat and try again." | `"false"` |
| `NO_MOVEMENT_DETECTED` | Hip keypoint vertical velocity near zero — person is static | "The video looks still. Make sure the camera is filming your full movement." | `"false"` |
| `NO_REPS_DETECTED` | Hip velocity data exists but rep segmentation found 0 complete cycles | "We couldn't detect a full squat rep. Make sure your full body is visible and complete at least one rep." | `"false"` |
| `BIOMECHANICS_COMPUTE_ERROR` | Unhandled exception in S3 Python script | "Something went wrong reading your movement data. Try re-uploading." | `"true"` |

---

### Haiku Call 1 — `error_stage: "haiku_call_1"` *(Added May 19, 2026 — replaces `nemotron` stage)*

**Owner: S2 — Backend calls Anthropic API · S2 fires the error event.**
Blocks Tab 1. If Haiku Call 1 fails, no results are available and Tab 2 never starts.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `HAIKU_TIMEOUT` | Anthropic API call exceeds timeout | "Form analysis is taking longer than expected. We'll retry automatically — hang tight." | `"true"` |
| `HAIKU_INVALID_OUTPUT` | Response missing required fields or malformed JSON | "The AI couldn't complete your form analysis. Try re-uploading — if it persists, let us know." | `"true"` |
| `HAIKU_CONTEXT_OVERFLOW` | Prompt too large — video too long or biomechanics JSON exceeds token limit | "That video is too long for detailed analysis. Try uploading a 30–60 second clip." | `"false"` |
| `HAIKU_API_ERROR` | Anthropic API returns 5xx or rate limit hit | "We hit a temporary issue with our AI service. Please try again in a moment." | `"true"` |

---

### OpenCV Part 2 — `error_stage: "opencv_part_2"` *(Added May 19, 2026 — replaces `frame_extraction` stage)*

**Owner: S3 runs OpenCV · S2 fires the error event.**
Non-blocking — Tab 1 coaching text is already visible. Image placeholder just stays as placeholder. Use `retryable: "partial"` — no blocking CTA.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FRAME_EXTRACTION_FAILED` | OpenCV can't seek to `bottom_timestamp_ms` — video file corrupt or timestamp missing | "We couldn't generate the form snapshot. Your coaching is still fully available above." | `"partial"` |
| `ANNOTATION_FAILED` | Frame extracted but OpenCV failed to draw overlays or save to GCS | "We couldn't generate the form snapshot. Your coaching is still fully available above." | `"partial"` |

> Both errors are `partial` — Tab 1 renders with coaching text. `annotated_frame_url` is null. Show coaching only, no image.

---

### Haiku Call 2 — `error_stage: "haiku_call_2"` *(Added May 19, 2026 — replaces `claude` stage)*

**Owner: S2 — Backend calls Anthropic API async · S2 fires the error event.**
Async — Tab 1 is already fully visible. Failure only affects Tab 2. Use `retryable: "partial"` — Tab 1 is always unaffected.

| error_code | Trigger | User-facing message (Tab 2 only) | retryable |
|---|---|---|---|
| `HAIKU_CALL_2_TIMEOUT` | Anthropic API call for longitudinal coaching exceeds timeout | "Progression data is taking longer than expected. Try tapping the tab again in a moment." | `"partial"` |
| `HAIKU_CALL_2_ERROR` | Malformed response or API error | "We couldn't load your progression data. Your form analysis above is complete and saved." | `"partial"` |
| `NO_PREVIOUS_SESSION` | No prior completed analysis for same `exercise_id` + `user_id` | "This is your first session for this exercise — progression tracking will appear after your next upload." | `"false"` |

---

### Infrastructure / Pipeline — `error_stage: "pipeline"`

**Owner: S2 — Backend infrastructure · S2 fires the error event.**

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `PIPELINE_TIMEOUT` | Total pipeline > 5 min | "Your analysis is taking unusually long. We've flagged it — try again and your previous data is saved." | `"true"` |
| `SYSTEM_ERROR` | Worker crash, OOM, unhandled exception | "Something went wrong on our end. Your video is saved — try again in a moment." | `"true"` |

---

## 4. HTTP Error Codes

### `POST /upload` — S1 sends · S2 receives · S2 returns HTTP status

| HTTP Status | When | Response body | FE action |
|---|---|---|---|
| `400 Bad Request` | Required field missing in POST body | `{ "error": "MISSING_FIELD", "field": "exercise_id" }` | Show inline validation error on upload form |
| `413 Payload Too Large` | File > 500 MB caught at server | `{ "error": "FILE_TOO_LARGE" }` | Show file size error |
| `415 Unsupported Media Type` | Wrong MIME type reaches server | `{ "error": "FORMAT_UNSUPPORTED" }` | Show format error |
| `500 Internal Server Error` | S2 crashed before SSE stream opened | `{ "error": "SYSTEM_ERROR" }` | Show generic "Something went wrong" + "Try again" |
| `503 Service Unavailable` | S2 pipeline infrastructure down | `{ "error": "SERVICE_UNAVAILABLE" }` | Show "Service is temporarily down — try again shortly" |

### `GET /analysis/{id}/result` — S1 requests on `analysis_ready` · S2 returns

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Haiku Call 1 complete, results available | Render Tab 1 results screen |
| `202 Accepted` | Pipeline still in progress | Show processing/waiting screen. |
| `404 Not Found` | `analysis_id` does not exist | Show "Analysis not found" — navigate back to upload |
| `500 Internal Server Error` | S2 DB read failed | Show "Couldn't load your results — try refreshing" |

### `GET /analysis/{id}/progression` — S1 requests on `progression_ready` · S2 returns *(Updated May 19, 2026 — replaces `/comparison`)*

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Haiku Call 2 complete, progression data available | Render Tab 2 — Section 1 + Section 2 |
| `202 Accepted` | Haiku Call 2 still generating | Show loading state in Tab 2 |
| `404 Not Found` | `analysis_id` does not exist | Hide Tab 2 |
| `500 Internal Server Error` | S2 DB read failed | Show "Progression unavailable — try refreshing" inline in Tab 2 |

---

## 5. Roadmap Task IDs

| Role | Squad | Task | Notes |
|---|---|---|---|
| Defines SSE shapes | S1 | S1-W5-03 | FE JSON schema including SSE event shapes (this file) |
| Defines SSE contract | S1 | S1-W5-06 | SSE skeleton — all event names + payloads delivered to S2 |
| Emits server-side | S2 | S2-W7-06 | S2 emits correct SSE events at each pipeline stage |
| Wires client-side | S1 | S1-W7-01 | S1 wires SSE to Tab 1 — `analysis_ready` triggers Results screen |
| Schema patches | S2 | PATCH-S2-W7-B | Update SSE contract — retire old events, add new events |

---

## Changelog
- May 19, 2026: Full rewrite — Nemotron → Haiku 4.5 architecture.
  - Removed events: `overlay_complete`, `nemotron_started`, `nemotron_complete`, `frames_extracting`, `frames_ready`, `rag_started`, `rag_complete`, `claude_started`, `claude_complete`, `analysis_complete`, `comparison_ready`
  - Added events: `haiku_started`, `analysis_ready` (Tab 1 unlocks), `frame_ready` (image loads ~2–3s later), `progression_ready` (Tab 2 unlocks async)
  - `error_stage` enum updated: removed `nemotron`, `frame_extraction`, `rag`, `claude` → added `haiku_call_1`, `opencv_part_2`, `haiku_call_2`
  - Error codes: `NEMOTRON_*` → `HAIKU_*` · `CLAUDE_*` → `HAIKU_CALL_2_*` · RAG errors removed
  - HTTP endpoint: `/analysis/{id}/comparison` → `/analysis/{id}/progression`
  - Stream lifecycle: closes after `progression_ready` (not `analysis_complete`)
- May 12, 2026: Initial definition — all SSE events, error taxonomy, HTTP codes, frontend UI copy, CTA logic, squad ownership
