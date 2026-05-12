# Kinetic — SSE Events, Error Codes & Frontend Messages
**Task:** S1-W5-06a  
**Last updated:** May 12, 2026  
**Scope:** SSE event shapes · Error taxonomy · HTTP error codes · Frontend UI copy  
**Produced by:** S2 — Backend  
**Consumed by:** S1 — Frontend

---

## How SSE Works in Kinetic

The frontend POSTs to `/upload` and the backend **keeps the response open** as a streaming connection (`Content-Type: text/event-stream`). Events fire as the pipeline progresses. The connection closes when `analysis_complete` or `error` fires.

```
Frontend                          Backend
   |                                 |
   |--- POST /upload --------------> |
   |                                 | upload_received fires
   |<-- SSE stream opens ----------- |
   |<-- upload_received ------------ |
   |<-- mediapipe_started ---------- |
   |<-- mediapipe_complete --------- |
   |<-- biomechanics_complete ------ |
   |<-- nemotron_started ----------- |
   |<-- nemotron_complete ---------- |
   |<-- frames_extracting ---------- |
   |<-- frames_ready --------------- |
   |<-- rag_started ---------------- |
   |<-- rag_complete --------------- |
   |<-- claude_started ------------- |
   |<-- claude_complete ------------ |
   |<-- analysis_complete ---------- |  ← stream closes
   |                                 |
   |--- GET /analysis/{id}/result -> |  ← frontend navigates to Results screen
   |<-- form analysis response ------ |
```

> The `comparison_ready` event fires **after** `analysis_complete` on a separate async path — the frontend listens for it to enable the comparison tab. See Section 3.

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
Fires immediately after the backend receives and stores the video to GCS and writes the initial `form_analyses` row.

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
Fires when the MediaPipe pose detection job begins.

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
| `video_url` | string (GCS URI) | No | Internal reference. Do not display or link. GCS URIs are not public URLs. |

**Suggested UI copy:** "Detecting your movement..."

---

### `mediapipe_complete`
Fires when pose detection finishes. Confirms how many reps and frames were processed.

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

### `biomechanics_complete`
Fires when the joint angle and biomechanics script finishes running on the keypoints.

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
Fires when the Nemotron form analysis job begins.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "video_url":   "gs://..."
}
```

> `video_url` is only present if video is sent to Nemotron directly (pending S2-W6-05 test results). Frontend should not depend on it being present — treat as optional.

**Suggested UI copy:** "Analysing your form..."

---

### `nemotron_complete`
Fires when Nemotron returns scored output with issue detection.

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
Fires when OpenCV begins extracting annotated frames from the video.

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
Fires when frame extraction is complete and annotated frames are stored in GCS.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid",
  "frame_url":   "gs://kinetic-videos/videos/{user_id}/{analysis_id}/frames/frame_bottom.jpg"
}
```

> `frame_url` is a GCS URI — not a public URL. The results screen uses `annotated_frame_url` from the API response (Section 1 of FE_Response_Schemas.md), not this GCS URI directly.

**Suggested UI copy:** "Frames captured"

---

### `rag_started`
Fires when the biomechanics knowledge retrieval begins.

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
Fires when the RAG retrieval finishes.

```json
{
  "analysis_id":       "uuid",
  "session_id":        "uuid",
  "user_id":           "uuid",
  "passages_retrieved": 8
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `passages_retrieved` | integer | No | Number of research passages retrieved. Internal — not required to display. |

**Suggested UI copy:** "Almost there — writing your report..."

---

### `claude_started`
Fires when the Claude Sonnet coaching generation begins.

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
Fires when Claude finishes and the coaching output is written to DB.

```json
{
  "analysis_id":      "uuid",
  "session_id":       "uuid",
  "user_id":          "uuid",
  "recommendation":   "hold"
}
```

| Field | Type | Nullable | Range / Max | Format | FE Note |
|---|---|---|---|---|---|
| `recommendation` | enum | No | `hold` \| `progress` \| `drop` | — | Can preview recommendation before full results load. Not required. |

**Suggested UI copy:** "Done! Loading your results..."

---

### `analysis_complete`
Final pipeline event. Signals the frontend to navigate to the Results screen.

```json
{
  "analysis_id":    "uuid",
  "session_id":     "uuid",
  "user_id":        "uuid",
  "full_result_url": "/analysis/{analysis_id}/result"
}
```

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `full_result_url` | string (path) | No | Relative path. Frontend navigates to this route to load results. |

**Frontend action on receipt:** Navigate to `full_result_url`. SSE stream closes.

---

## 2. Error SSE Event

A single `error` event shape is used across all pipeline stages. The `error_stage` and `error_code` fields identify exactly what failed.

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

Fires asynchronously **after** `analysis_complete`, once the comparison coaching is generated. Does not block the results screen from loading.

```json
{
  "analysis_id": "uuid",
  "session_id":  "uuid",
  "user_id":     "uuid"
}
```

**Frontend action on receipt:** Enable the Form Comparison tab on the Results screen.  
**If tab is opened before event fires:** Show a brief loading state (expected < 5s after `analysis_complete`).  
**If no previous session exists:** Backend stores `has_comparison: false` immediately — `comparison_ready` still fires so the tab can show the empty state.

---

## 4. Error Code Taxonomy

### Pre-upload — client-side only, never reaches SSE

These are validated by the frontend before the POST request is sent.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FILE_TOO_LARGE` | > 500 MB | "That video is too large (max 500 MB). Try trimming it to your working set." | `"false"` |
| `FORMAT_UNSUPPORTED` | Not `.mp4` / `.mov` / `.avi` | "We can't read that format. Export as MP4 and try again." | `"false"` |
| `FILE_CORRUPT` | Zero bytes or unreadable header | "That file looks corrupted. Re-export from your camera roll and try again." | `"false"` |
| `UPLOAD_TIMEOUT` | Network drop mid-transfer | "Upload timed out. Check your connection and try again." | `"true"` |

---

### Quality Gate — `error_stage: "quality_gate"` · V2

Fires **before any AI processing**. If the video fails the quality gate, the pipeline stops here and no AI costs are incurred. All quality gate errors: `retryable: "false"` — the video must be re-filmed.

> **`landmark_medians` field:** For `occlusion_left_side`, `occlusion_right_side`, `occlusion_both_sides`, `out_of_frame_left`, `out_of_frame_right` — the error payload also includes a `landmark_medians` object with `median_visibility` and `median_presence` per critical landmark (knee/hip/heel, both sides). Frontend uses these to confirm the left/right message variant is correct. Not present for `poor_video_quality`, `no_reps_detected`, or `insufficient_reps`.

| error_code | Gate | Trigger condition | User-facing message | retryable |
|---|---|---|---|---|
| `occlusion_left_side` | M1 | ≥1 of knee/hip/heel on left side has visibility ≤ 0.60. Right side passes. | "Part of your left side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_right_side` | M1 | ≥1 of knee/hip/heel on right side has visibility ≤ 0.60. Left side passes. | "Part of your right side was hidden from view. Rather than switching sides, rotate your camera slightly toward the front of your body." | `"false"` |
| `occlusion_both_sides` | M2 | ≥1 of knee/hip/heel has visibility ≤ 0.60 on both sides. | "We couldn't see your lower body clearly. Try angling your camera slightly toward the front so both legs are fully in view." | `"false"` |
| `out_of_frame_left` | M3 | Visibility passes but ≥1 of knee/hip/heel on left side has median_presence ≤ 0.50. | "Your left side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `out_of_frame_right` | M3 | Visibility passes but ≥1 of knee/hip/heel on right side has median_presence ≤ 0.50. | "Your right side kept moving out of frame. Move the camera back slightly so your full body stays visible throughout the squat." | `"false"` |
| `poor_video_quality` | M4 | `video_score` < 0.70. No landmark hit the 0.60 hard floor. Typical: filming from behind, obstruction, low lighting. | "We couldn't read your body position clearly. Film from your side with good lighting and a clear background." | `"false"` |
| `no_reps_detected` | M5 | `complete_reps` = 0. A complete rep requires both "top" and "bottom" position detected in the same rep segment. | "We couldn't detect any squats in your video. Make sure you're doing goblet squats and your full body is in frame from the start." | `"false"` |
| `insufficient_reps` | M6 | 0 < `complete_reps` < 3. | "Film a full set to get your analysis. We need at least 3 complete reps — squat all the way down and all the way back up for each one." | `"false"` |

---

### Biomechanics — `error_stage: "biomechanics"`

MediaPipe ran fine and produced keypoints, but the Python script could not compute valid metrics from them.

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `VIDEO_TOO_SHORT` | Video < 5s — not enough frames for rep segmentation | "We didn't catch a complete rep. Record at least one full squat and try again." | `"false"` |
| `NO_MOVEMENT_DETECTED` | Hip keypoint vertical velocity near zero — person is static | "The video looks still. Make sure the camera is filming your full movement." | `"false"` |
| `NO_REPS_DETECTED` | Hip velocity data exists but rep segmentation found 0 complete cycles | "We couldn't detect a full squat rep. Make sure your full body is visible and complete at least one rep." | `"false"` |
| `BIOMECHANICS_COMPUTE_ERROR` | Unhandled exception in Python script (e.g. division by zero, missing keypoint index) | "Something went wrong reading your movement data. Try re-uploading." | `"true"` |

---

### Nemotron — `error_stage: "nemotron"`

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `NEMOTRON_TIMEOUT` | API call exceeds timeout | "Form analysis is taking longer than expected. We'll retry automatically — hang tight." | `"true"` |
| `NEMOTRON_NO_OUTPUT` | Response empty or malformed | "The AI couldn't interpret your movement data. Try re-uploading — if it persists, let us know." | `"true"` |
| `NEMOTRON_CONTEXT_OVERFLOW` | Video too long → token limit hit | "That video is too long for detailed analysis. Try uploading a 30–60 second clip." | `"false"` |

---

### Frame Extraction — `error_stage: "frame_extraction"`

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `FRAME_EXTRACTION_FAILED` | OpenCV can't seek to Nemotron timestamp | "We identified form issues but couldn't extract the frames to show you. Your text coaching is still available below." | `"partial"` |

> `partial` — results screen still loads. Annotated frame is null. Show text coaching only, no image overlay.

---

### RAG — `error_stage: "rag"`

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `RAG_UNAVAILABLE` | Vector DB timeout or service down | "Coaching library is temporarily unavailable. Your form analysis is ready, but personalised drills may be limited." | `"partial"` |
| `RAG_NO_RESULTS` | No matching coaching context found | "We couldn't find specific drills for your movement pattern yet. General coaching below." | `"partial"` |

> Both RAG errors are `partial` — pipeline continues to Claude without RAG context. Results still load.

---

### Claude — `error_stage: "claude"`

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `CLAUDE_TIMEOUT` | Claude API exceeds timeout | "Your coaching report is taking longer than expected. Refreshing should show your results shortly." | `"true"` |
| `CLAUDE_ERROR` | Malformed or empty Claude response | "We hit a snag writing your coaching report. Your raw form data is saved — try refreshing." | `"true"` |

---

### Infrastructure / Pipeline — `error_stage: "pipeline"`

| error_code | Trigger | User-facing message | retryable |
|---|---|---|---|
| `PIPELINE_TIMEOUT` | Total pipeline > 5 min | "Your analysis is taking unusually long. We've flagged it — try again and your previous data is saved." | `"true"` |
| `SYSTEM_ERROR` | Worker crash, OOM, unhandled exception | "Something went wrong on our end. Your video is saved — try again in a moment." | `"true"` |

---

## 5. HTTP Error Codes

These are returned as standard HTTP responses, not SSE events. They fire before or instead of the SSE stream opening.

### `POST /upload`

| HTTP Status | When | Response body | FE action |
|---|---|---|---|
| `400 Bad Request` | Required field missing in POST body (exercise_id, weight_value, etc.) | `{ "error": "MISSING_FIELD", "field": "exercise_id" }` | Show inline validation error on upload form |
| `413 Payload Too Large` | File > 500 MB caught at server before client-side check | `{ "error": "FILE_TOO_LARGE" }` | Show file size error (same copy as pre-upload `FILE_TOO_LARGE`) |
| `415 Unsupported Media Type` | Wrong MIME type reaches server | `{ "error": "FORMAT_UNSUPPORTED" }` | Show format error (same copy as pre-upload `FORMAT_UNSUPPORTED`) |
| `500 Internal Server Error` | Server crashed before SSE stream opened | `{ "error": "SYSTEM_ERROR" }` | Show generic "Something went wrong" + "Try again" |
| `503 Service Unavailable` | Pipeline infrastructure down | `{ "error": "SERVICE_UNAVAILABLE" }` | Show "Service is temporarily down — try again shortly" |

### `GET /analysis/{id}/result`

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Analysis complete and results available | Render results screen |
| `202 Accepted` | Pipeline still in progress (user navigated directly) | Show processing/waiting screen. Resume SSE polling if needed. |
| `404 Not Found` | `analysis_id` does not exist | Show "Analysis not found" — navigate back to upload |
| `500 Internal Server Error` | DB read failed | Show "Couldn't load your results — try refreshing" |

### `GET /analysis/{id}/comparison`

| HTTP Status | When | FE action |
|---|---|---|
| `200 OK` | Comparison data available (`has_comparison: true` or `false`) | Render comparison tab |
| `202 Accepted` | Async comparison still generating | Show brief loading state in tab |
| `404 Not Found` | `analysis_id` does not exist | Hide comparison tab |
| `500 Internal Server Error` | DB read failed | Show "Comparison unavailable — try refreshing" inline in tab |

---

## 6. Roadmap Task IDs

| Role | Task | Notes |
|---|---|---|
| Defines shapes | S1-W5-03 | FE JSON schema including SSE event shapes (this file) |
| Defines contract | S1-W5-06 | SSE skeleton — all event names + payloads delivered to S2 |
| Emits server-side | S2-W6-06 | S2 emits correct SSE events at each pipeline stage |
| Wires client-side | S1-W6-03 | S1 wires SSE to real processing states — tested against S2 stub endpoint |

---

## Changelog
- May 12, 2026: Initial definition — all SSE events, error taxonomy (pre-upload + 7 pipeline stages), HTTP error codes, frontend UI copy, CTA logic
