# Kinetic — SSE Events, Error Codes & Frontend Messages
**Task:** S1-W5-06a  
**Last updated:** May 12, 2026  
**Scope:** SSE event shapes · Error taxonomy · HTTP error codes · Frontend UI copy  
**Produced by:** S2 — Backend  
**Consumed by:** S1 — Frontend

---

## How SSE Works in Kinetic

**Two separate connections — Option B (confirmed):**

1. `POST /upload` returns `{"analysis_id": "uuid"}` as normal JSON immediately — no streaming, closes right away.
2. S1 opens a separate `EventSource` at `GET /analysis/{analysis_id}/stream` to receive live pipeline events.

The stream opens and holds until `analysis_complete` or `error` fires, then closes.

```
Frontend (S1)                     Backend (S2)                    AI/MediaPipe (S3)
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
   |                                 |--- run OpenCV overlay --------> |
   |                                 |<-- overlay_video_url returned - |
   |<-- overlay_complete ----------- |                                 |
   |                                 |<-- biomechanics JSON returned - |
   |<-- biomechanics_complete ------ |                                 |
   |                                 |--- dispatch Nemotron job -----> |
   |<-- nemotron_started ----------- |                                 |
   |                                 |<-- scored output returned ----- |
   |<-- nemotron_complete ---------- |                                 |
   |<-- frames_extracting ---------- | (S2 runs OpenCV internally)     |
   |<-- frames_ready --------------- |                                 |
   |<-- rag_started ---------------- | (S2 injects MD files)           |
   |<-- rag_complete --------------- |                                 |
   |<-- claude_started ------------- | (S2 calls Claude API)           |
   |<-- claude_complete ------------ |                                 |
   |<-- analysis_complete ---------- |  ← stream closes               |
   |                                 |                                 |
   |--- GET /analysis/{id}/result -> |                                 |
   |<-- form analysis response ------ |                                |
```

> The `comparison_ready` event fires **after** `analysis_complete` on a separate async path — S2 runs a second Claude call. Frontend listens to enable the comparison tab. See Section 3.

---

## Squad Dependencies Overview

| Event | Fired by | Consumed by | Inter-squad dependency |
|---|---|---|---|
| `upload_received` | S2 | S1 | S1 POST triggers S2 |
| `mediapipe_started` | S2 | S1 | S2 dispatches job to S3 — **S3 must be ready to accept jobs** |
| `mediapipe_complete` | S2 | S1 | **S3 must return keypoints to S2** before S2 can fire this |
| `overlay_complete` | S2 | S1 | **S3 must complete OpenCV skeleton overlay and return overlay_video_url to S2** before S2 can fire this |
| `biomechanics_complete` | S2 | S1 | **S3 must return biomechanics JSON to S2** before S2 can fire this |
| `nemotron_started` | S2 | S1 | S2 dispatches to Nemotron via S3 — **S3 owns Nemotron integration** |
| `nemotron_complete` | S2 | S1 | **S3 must return Nemotron scored output to S2** before S2 can fire this |
| `frames_extracting` | S2 | S1 | S2-internal (OpenCV) — no S3 dependency |
| `frames_ready` | S2 | S1 | S2-internal (OpenCV) — no S3 dependency |
| `rag_started` | S2 | S1 | S2-internal — no S3 dependency |
| `rag_complete` | S2 | S1 | S2-internal — no S3 dependency |
| `claude_started` | S2 | S1 | S2-internal — no S3 dependency |
| `claude_complete` | S2 | S1 | S2-internal — no S3 dependency |
| `analysis_complete` | S2 | S1 | All upstream stages must complete |
| `comparison_ready` | S2 | S1 | Async — S2 runs a second Claude call after `analysis_complete` |
| `error` | S2 (pipeline errors) or S1 (pre-upload) | S1 | Stage-dependent — see error taxonomy |

**SSE contract handshake between squads:**

| Step | Who | Task | Dependency |
|---|---|---|---|
| 1 | S1 defines SSE contract | S1-W5-06 | S1 delivers event names + payloads to S2 **before S2 builds emission** |
| 2 | S2 builds server-side emission | S2-W6-06 | Blocked on S1-W5-06 |
| 3 | S2 exposes stub SSE endpoint | S2-W6-06 | Endpoint: `GET /analysis/{id}/stream` — S1 needs this to test client wiring |
| 4 | S1 wires client-side | S1-W6-03 | S1 opens `EventSource("/analysis/{id}/stream")` after receiving `analysis_id` from POST /upload response |

**S2 ↔ S3 output format dependency:**  
S2 fires `mediapipe_complete`, `biomechanics_complete`, and `nemotron_complete` using data returned by S3. S2 must not hardcode field assumptions — S3 output schemas defined in `Kinetic_Biomechanics_Output_Schema.json` and `Nemotron_Testing_Guide.docx` are the contract. Any S3 schema change must be communicated to S2 before S2 builds the emission logic.

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

### `upload_received`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None

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

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `filename` | string | No | max 255 chars | — | Original filename as uploaded. Display in processing screen if helpful. |
| `size_mb` | float | No | 0 – 500 | 2 dp | Internal reference. Not required to display. |
| `created_at` | timestamp | No | — | ISO 8601 UTC | Not displayed at this stage — used later in results. |

**Suggested UI copy:** "Video received — starting analysis"

---

### `mediapipe_started`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S2 dispatches MediaPipe job to S3 immediately before firing this

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

**Suggested UI copy:** "Detecting your movement..."

---

### `mediapipe_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S3 must return keypoints to S2 before S2 fires this

Fires when S3 returns MediaPipe keypoints to S2 and pose detection is confirmed complete.

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

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `rep_count` | integer | No | 1 – 99 | — | Can surface as "X reps detected" on processing screen. |
| `fps` | integer | No | 1 – 240 | — | Internal. Not required to display. |
| `keypoints_detected` | integer | No | 33 (fixed for MediaPipe) | — | Internal. Not required to display. |
| `frames_processed` | integer | No | 1 – 99,999 | — | Internal. Not required to display. |

**Suggested UI copy:** "Movement detected — {rep_count} reps found"

---

### `overlay_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S3 must complete OpenCV skeleton overlay and return overlay_video_url to S2

Fires when S3 finishes drawing the skeleton overlay on the full video. The overlay video is the visual input sent to Nemotron — it is not shown to the user.

```json
{
  "analysis_id":       "uuid",
  "session_id":        "uuid",
  "user_id":           "uuid",
  "overlay_video_url": "gs://kinetic-videos/analyses/{analysis_id}/overlay.mp4"
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `overlay_video_url` | string (GCS URI) | No | GCS path of the skeleton overlay video. Not shown to user — passed to Nemotron as AI input. |

**Suggested UI copy:** "Processing your movement..."

---

### `biomechanics_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S3 must return biomechanics JSON to S2 before S2 fires this

Fires when S3 returns the joint angle and biomechanics output to S2.

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

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `rep_count` | integer | No | 1 – 99 | — | Same as mediapipe_complete — confirms consistency. |
| `joints_computed` | integer | No | 1 – 33 | — | Internal. Not required to display. |
| `avg_confidence` | float | No | 0.00 – 1.00 | 2 dp | Internal. Not required to display. |

**Suggested UI copy:** "Calculating joint angles..."

---

### `nemotron_started`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S2 dispatches to Nemotron via S3 immediately before firing this — S3 owns Nemotron integration

Fires when S2 dispatches the Nemotron form analysis job.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "video_url":   "gs://..."
}
```

> `video_url` is only present if video is sent to Nemotron directly (pending S2-W6-05 test results). Frontend should not depend on it — treat as optional.

**Suggested UI copy:** "Analysing your form..."

---

### `nemotron_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** S3 must return Nemotron scored output to S2 before S2 fires this

Fires when S3 returns Nemotron output (scores, issues, chain of thought) to S2.

```json
{
  "analysis_id":   "uuid",
  "session_id":    "uuid",
  "user_id":       "uuid",
  "overall_score": 72,
  "issues_count":  2
}
```

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `overall_score` | integer | No | 0 – 100 | — | Can show as teaser on processing screen if desired. Not the final score. |
| `issues_count` | integer | No | 0 – 99 | — | Internal. Not required to display. |

**Suggested UI copy:** "Form analysis complete — generating your coaching..."

---

### `frames_extracting`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 runs OpenCV internally

Fires when S2 begins extracting annotated frames from the video using OpenCV.

```json
{
  "analysis_id":  "uuid",
  "session_id":   "uuid",
  "user_id":      "uuid",
  "video_url":    "gs://...",
  "frames_total": 12
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `frames_total` | integer | No | Total frames to extract. Can be used for a progress indicator if implemented. |

**Suggested UI copy:** "Capturing key frames..."

---

### `frames_ready`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 runs OpenCV internally

Fires when S2 finishes frame extraction and stores annotated frames in GCS.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "frame_url":   "gs://kinetic-videos/videos/{user_id}/{analysis_id}/frames/frame_bottom.jpg"
}
```

> `frame_url` is a GCS URI — not a public URL. The results screen uses `annotated_frame_url` from the API response (FE_Response_Schemas.md Section 1), not this GCS URI directly.

**Suggested UI copy:** "Frames captured"

---

### `rag_started`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 queries vector DB internally

Fires when S2 begins retrieving biomechanics knowledge from the vector DB.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Suggested UI copy:** "Looking up coaching knowledge..."

---

### `rag_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 queries vector DB internally

Fires when S2 finishes RAG retrieval.

```json
{
  "analysis_id":        "uuid",
  "session_id":         "uuid",
  "user_id":            "uuid",
  "passages_retrieved": 8
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `passages_retrieved` | integer | No | Number of research passages retrieved. Internal — not required to display. |

**Suggested UI copy:** "Almost there — writing your report..."

---

### `claude_started`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 calls Claude API internally

Fires when S2 begins the Claude Sonnet coaching generation call.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Suggested UI copy:** "Writing your personalised coaching..."

---

### `claude_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 calls Claude API internally

Fires when Claude returns and S2 writes coaching output to DB.

```json
{
  "analysis_id":    "uuid",
  "session_id":     "uuid",
  "user_id":        "uuid",
  "recommendation": "hold"
}
```

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `recommendation` | enum | No | `hold` \| `progress` \| `drop` | — | Can preview on processing screen before results load. Not required. |

**Suggested UI copy:** "Done! Loading your results..."

---

### `analysis_complete`
**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** All upstream S3 stages (MediaPipe, Biomechanics, Nemotron) must be complete

Final pipeline event. S1 navigates to the Results screen on receipt.

```json
{
  "analysis_id":     "uuid",
  "session_id":      "uuid",
  "user_id":         "uuid",
  "full_result_url": "/analysis/{analysis_id}/result"
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `full_result_url` | string (path) | No | Relative path. Frontend navigates to this route to load results. |

**Frontend action on receipt:** Navigate to `full_result_url`. SSE stream closes.

---

## 2. Error SSE Event

**Fired by:** S2 — Backend (all pipeline stages) or S1 — Frontend (pre-upload validation only)  ·  **Consumed by:** S1 — Frontend

A single `error` event shape is used across all pipeline stages. `error_stage` and `error_code` identify exactly what failed.

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

**Field Reference**

| Field | Type | Nullable | Values | FE Note |
|---|---|---|---|---|
| `error_code` | enum (string) | No | See taxonomy below | Use this to look up user-facing copy. All caps snake_case. |
| `error_stage` | enum (string) | No | `quality_gate` · `biomechanics` · `nemotron` · `frame_extraction` · `rag` · `claude` · `pipeline` | Identifies which pipeline stage failed. |
| `retryable` | enum (string) | No | `"true"` · `"false"` · `"partial"` | **This is a string, not a boolean.** Use string comparison: `retryable === "true"`. Never check truthiness — the string `"false"` is truthy in JS. |
| `message` | string | No | max 500 chars | **Internal log message — never show to user.** Frontend derives user-facing copy from `error_code`. |

**CTA logic based on `retryable`:**

| Value | Meaning | Frontend action |
|---|---|---|
| `"true"` | Infra failure — same video is fine | Show **"Try again"** button. Re-submit the same upload. |
| `"false"` | Video itself must change | Show **"Re-film and upload"** button. Navigate back to upload screen. |
| `"partial"` | Pipeline degraded but continues | Show **inline warning** — no blocking CTA. Results still load. |

---

## 3. Comparison Ready Event

**Fired by:** S2 — Backend  ·  **Consumed by:** S1 — Frontend  ·  **S3 dependency:** None — S2 runs a second Claude call internally after `analysis_complete`

Fires asynchronously **after** `analysis_complete`. Does not block the results screen from loading.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Frontend action on receipt:** Enable the Form Comparison tab on the Results screen.  
**If tab is opened before event fires:** Show a brief loading state (expected < 5s after `analysis_complete`).  
**If no previous session exists:** S2 stores `has_comparison: false` immediately — `comparison_ready` still fires so the tab can show the empty state.

---

## 4. Error Code Taxonomy

### Pre-upload — S1 validates client-side only · never reaches SSE

**Owner: S1 — Frontend.** These checks run in the browser before the POST request is sent. S2 never sees these errors.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FILE_TOO_LARGE` | > 500 MB | "That video is too large (max 500 MB). Try trimming it to your working set." | `"false"` |
| `FORMAT_UNSUPPORTED` | Not `.mp4` / `.mov` / `.avi` | "We can't read that format. Export as MP4 and try again." | `"false"` |
| `FILE_CORRUPT` | Zero bytes or unreadable header | "That file looks corrupted. Re-export from your camera roll and try again." | `"false"` |
| `UPLOAD_TIMEOUT` | Network drop mid-transfer | "Upload timed out. Check your connection and try again." | `"true"` |

---

### Quality Gate — `error_stage: "quality_gate"` · V2

**Owner: S3 evaluates · S2 fires the error event.**  
S3 runs the Landmark Quality Framework against the MediaPipe keypoints and returns a pass/fail result to S2. S2 fires the `error` SSE event using that result. Fires **before any AI processing** — if rejected here, no Nemotron or Claude calls are made.

All quality gate errors: `retryable: "false"` — the video must be re-filmed.

> **`landmark_medians` field:** For `occlusion_*` and `out_of_frame_*` codes, the error payload also includes a `landmark_medians` object with `median_visibility` and `median_presence` per critical landmark (knee/hip/heel, both sides). Frontend uses this to confirm the left/right message variant. Not present for `poor_video_quality`, `no_reps_detected`, or `insufficient_reps`.

| error_code | Gate | Trigger condition | User-facing message | retryable |
|---|---|---|---|---|
| `occlusion_left_side` | M1 | ≥1 of knee/hip/heel on left side visibility ≤ 0.60. Right side passes. | "Part of your left side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_right_side` | M1 | ≥1 of knee/hip/heel on right side visibility ≤ 0.60. Left side passes. | "Part of your right side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_both_sides` | M2 | ≥1 of knee/hip/heel visibility ≤ 0.60 on both sides. | "We couldn't see your lower body clearly. Try angling your camera slightly toward the front so both legs are fully in view." | `"false"` |
| `out_of_frame_left` | M3 | Visibility passes but ≥1 of knee/hip/heel on left side median_presence ≤ 0.50. | "Your left side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `out_of_frame_right` | M3 | Visibility passes but ≥1 of knee/hip/heel on right side median_presence ≤ 0.50. | "Your right side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `poor_video_quality` | M4 | `video_score` < 0.70. Typical: filming from behind, obstruction, low lighting. | "We couldn't read your body position clearly. Film from your side with good lighting and a clear background." | `"false"` |
| `no_reps_detected` | M5 | `complete_reps` = 0. | "We couldn't detect any squats in your video. Make sure you're doing goblet squats and your full body is in frame from the start." | `"false"` |
| `insufficient_reps` | M6 | 0 < `complete_reps` < 3. | "Film a full set to get your analysis. We need at least 3 complete reps — squat all the way down and all the way back up for each one." | `"false"` |

---

### Biomechanics — `error_stage: "biomechanics"`

**Owner: S3 runs the script · S2 fires the error event.**  
MediaPipe ran and produced keypoints, but S3's Python biomechanics script could not compute valid metrics from them. S3 returns the failure to S2, which fires the error event.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `VIDEO_TOO_SHORT` | Video < 5s | "We didn't catch a complete rep. Record at least one full squat and try again." | `"false"` |
| `NO_MOVEMENT_DETECTED` | Hip keypoint vertical velocity near zero — person is static | "The video looks still. Make sure the camera is filming your full movement." | `"false"` |
| `NO_REPS_DETECTED` | Hip velocity data exists but rep segmentation found 0 complete cycles | "We couldn't detect a full squat rep. Make sure your full body is visible and complete at least one rep." | `"false"` |
| `BIOMECHANICS_COMPUTE_ERROR` | Unhandled exception in S3 Python script | "Something went wrong reading your movement data. Try re-uploading." | `"true"` |

---

### Nemotron — `error_stage: "nemotron"`

**Owner: S3 runs Nemotron · S2 fires the error event.**  
S3 owns the Nemotron API integration. If Nemotron fails, S3 returns the failure to S2, which fires the error event.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `NEMOTRON_TIMEOUT` | API call exceeds timeout | "Form analysis is taking longer than expected. We'll retry automatically — hang tight." | `"true"` |
| `NEMOTRON_NO_OUTPUT` | Response empty or malformed | "The AI couldn't interpret your movement data. Try re-uploading — if it persists, let us know." | `"true"` |
| `NEMOTRON_CONTEXT_OVERFLOW` | Video too long → token limit hit | "That video is too long for detailed analysis. Try uploading a 30–60 second clip." | `"false"` |

---

### Frame Extraction — `error_stage: "frame_extraction"`

**Owner: S2 — Backend runs OpenCV · S2 fires the error event.**  
This is fully within S2. No S3 dependency.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FRAME_EXTRACTION_FAILED` | OpenCV can't seek to Nemotron timestamp | "We identified form issues but couldn't extract the frames to show you. Your text coaching is still available below." | `"partial"` |

> `partial` — results screen still loads. `annotated_frame_url` is null. Show text coaching only, no image overlay.

---

### RAG — `error_stage: "rag"`

**Owner: S2 — Backend queries vector DB · S2 fires the error event.**  
Fully within S2. No S3 dependency.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `RAG_UNAVAILABLE` | Vector DB timeout or service down | "Coaching library is temporarily unavailable. Your form analysis is ready, but personalised drills may be limited." | `"partial"` |
| `RAG_NO_RESULTS` | No matching coaching context found | "We couldn't find specific drills for your movement pattern yet. General coaching below." | `"partial"` |

> Both RAG errors are `partial` — pipeline continues to Claude without RAG context. Results still load.

---

### Claude — `error_stage: "claude"`

**Owner: S2 — Backend calls Claude API · S2 fires the error event.**  
Fully within S2. No S3 dependency.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `CLAUDE_TIMEOUT` | Claude API exceeds timeout | "Your coaching report is taking longer than expected. Refreshing should show your results shortly." | `"true"` |
| `CLAUDE_ERROR` | Malformed or empty Claude response | "We hit a snag writing your coaching report. Your raw form data is saved — try refreshing." | `"true"` |

---

### Infrastructure / Pipeline — `error_stage: "pipeline"`

**Owner: S2 — Backend infrastructure · S2 fires the error event.**  
Worker-level failures. No S3 dependency.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `PIPELINE_TIMEOUT` | Total pipeline > 5 min | "Your analysis is taking unusually long. We've flagged it — try again and your previous data is saved." | `"true"` |
| `SYSTEM_ERROR` | Worker crash, OOM, unhandled exception | "Something went wrong on our end. Your video is saved — try again in a moment." | `"true"` |

---

## 5. HTTP Error Codes

### `POST /upload` — S1 sends · S2 receives · S2 returns HTTP status

| HTTP Status | When | Response body | FE action |
|---|---|---|---|
| `400 Bad Request` | Required field missing in POST body | `{ "error": "MISSING_FIELD", "field": "exercise_id" }` | Show inline validation error on upload form |
| `413 Payload Too Large` | File > 500 MB caught at server | `{ "error": "FILE_TOO_LARGE" }` | Show file size error (same copy as pre-upload `FILE_TOO_LARGE`) |
| `415 Unsupported Media Type` | Wrong MIME type reaches server | `{ "error": "FORMAT_UNSUPPORTED" }` | Show format error (same copy as pre-upload `FORMAT_UNSUPPORTED`) |
| `500 Internal Server Error` | S2 crashed before SSE stream opened | `{ "error": "SYSTEM_ERROR" }` | Show generic "Something went wrong" + "Try again" |
| `503 Service Unavailable` | S2 pipeline infrastructure down | `{ "error": "SERVICE_UNAVAILABLE" }` | Show "Service is temporarily down — try again shortly" |

### `GET /analysis/{id}/result` — S1 requests · S2 returns

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Analysis complete and results available | Render results screen |
| `202 Accepted` | Pipeline still in progress (user navigated directly) | Show processing/waiting screen. Resume SSE polling if needed. |
| `404 Not Found` | `analysis_id` does not exist | Show "Analysis not found" — navigate back to upload |
| `500 Internal Server Error` | S2 DB read failed | Show "Couldn't load your results — try refreshing" |

### `GET /analysis/{id}/comparison` — S1 requests · S2 returns

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Comparison data available (`has_comparison: true` or `false`) | Render comparison tab |
| `202 Accepted` | Async comparison still generating in S2 | Show brief loading state in tab |
| `404 Not Found` | `analysis_id` does not exist | Hide comparison tab |
| `500 Internal Server Error` | S2 DB read failed | Show "Comparison unavailable — try refreshing" inline in tab |

---

## 6. Roadmap Task IDs

| Role | Squad | Task | Notes |
|---|---|---|---|
| Defines SSE shapes | S1 | S1-W5-03 | FE JSON schema including SSE event shapes (this file) |
| Defines SSE contract | S1 | S1-W5-06 | SSE skeleton — all event names + payloads delivered to S2. **S2 blocked until this is done.** |
| Emits server-side | S2 | S2-W6-06 | S2 emits correct SSE events at each pipeline stage. Depends on S1-W5-06. |
| Wires client-side | S1 | S1-W6-03 | S1 wires SSE to processing states — tested against S2 stub endpoint. Depends on S2-W6-06 stub. |

---

## Changelog
- May 12, 2026: Initial definition — all SSE events, error taxonomy (pre-upload + 7 pipeline stages), HTTP error codes, frontend UI copy, CTA logic
- May 12, 2026: Added squad ownership and inter-squad dependencies to every event, error stage, HTTP endpoint, and roadmap task section
