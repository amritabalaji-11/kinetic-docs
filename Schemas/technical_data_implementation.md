# Kinetic — Technical Data Implementation & Error Messages
**Last updated:** May 25, 2026 (W8 async job error handling)  
**Scope:** Backend implementation details · Error message lifecycle · Retry strategies · Job tracking  
**Produced by:** S2 — Backend  
**Consumed by:** S1 — Frontend, S3 — Data/CV

---

## Overview

This document provides implementation guidance for SSE event emission and async job error handling. It maps error codes to backend exception types, defines retry strategies, and specifies the exact JSON payloads S2 must emit at each async job lifecycle stage.

---

## Part 1: Async Job Lifecycle & State Machine

### Job States

```
┌─────────┐         ┌──────────┐         ┌─────────┐         ┌──────────┐
│ PENDING │ ───────>│ QUEUED   │ ───────>│ RUNNING │ ───────>│ COMPLETE │
└─────────┘         └──────────┘         └─────────┘         └──────────┘
    (init)          (S2-W8-02)         (S2-W8-04)           (S2-W8-04)
                       ↓                    ↓                    ↓
                   emit queued_        emit started_         emit complete_
                   event               event                 event + output
                       
                                           ↓
                                      ┌────────────┐
                                      │  FAILED    │
                                      └────────────┘
                                      (at any stage)
                                           ↓
                                      emit job_failed
                                      event + error_code
```

**Two parallel jobs:**
1. **Haiku Call 2** — `haiku_call_2_*` events
2. **OpenCV Part 2** — `opencv_part_2_*` events

Both start simultaneously after `analysis_ready` event. Either can fail independently.

---

## Part 2: Error Codes & Implementation Mapping

### Error Code → Backend Exception Mapping

Use these mappings to catch exceptions and emit the correct SSE error event.

#### Haiku Call 2 Errors

| error_code | Backend Exception Type | Retry Strategy | Timeout | User Message |
|---|---|---|---|---|
| `HAIKU_CALL_2_TIMEOUT` | `anthropic.APITimeoutError` or wall-clock timeout > 120s | 3 retries: 1s, 3s, 9s exponential backoff | 120s | "Progression data is taking longer than expected. Try tapping the tab again in a moment." |
| `HAIKU_CALL_2_INVALID_OUTPUT` | `json.JSONDecodeError` / response missing required fields | Don't retry — invalid output won't fix on retry | — | "We couldn't generate your progression data. Your form analysis above is complete and saved." |
| `HAIKU_CALL_2_CONTEXT_OVERFLOW` | `anthropic.BadRequestError` with "context_window_exceeded" message | Don't retry — user needs shorter video/less history | — | "Your session history is too long for progression analysis. Form analysis remains complete." |
| `HAIKU_CALL_2_API_ERROR` | `anthropic.APIStatusError` (5xx or rate limit 429) | 3 retries: 2s, 5s, 10s exponential backoff | 120s | "Progression service temporarily unavailable. Try again in a moment." |
| `HAIKU_CALL_2_DB_WRITE_ERROR` | `sqlalchemy.exc.SQLAlchemyError` / database transaction failure | 2 retries: 1s, 3s backoff | 30s | "Progression saved partially — analysis complete above." |
| `NO_PREVIOUS_SESSION` | Query returns 0 rows for `exercise_id + user_id` | Don't retry — this is expected state | — | "This is your first session for this exercise — progression tracking will appear after your next upload." |

#### OpenCV Part 2 Errors

| error_code | Backend Exception Type | Retry Strategy | Timeout | User Message |
|---|---|---|---|---|
| `FRAME_EXTRACTION_FAILED` | `cv2.error` or timestamp not found in biomechanics JSON | 2 retries: 2s, 5s backoff | 60s | "We couldn't generate the form snapshot. Your coaching is still fully available above." |
| `ANNOTATION_FAILED` | `cv2.error` during drawing/overlay operations | 2 retries: 2s, 5s backoff | 60s | "We couldn't generate the form snapshot. Your coaching is still fully available above." |
| `OPENCV_TIMEOUT` | Job execution exceeds 60s wall-clock time | Don't retry — slow video or heavy load | 60s | "Form snapshot generation is taking longer — coaching available above." |
| `OPENCV_GCS_WRITE_ERROR` | `google.api_core.exceptions.GoogleAPICallError` during file upload | 3 retries: 2s, 5s, 10s backoff | 30s | "Form snapshot generated but couldn't be saved. Coaching analysis complete." |
| `OPENCV_DB_WRITE_ERROR` | `sqlalchemy.exc.SQLAlchemyError` writing `annotated_frame_url` to DB | 2 retries: 1s, 3s backoff | 30s | "Form snapshot partially saved. Coaching analysis complete." |

---

## Part 3: SSE Event Emission Pseudo-Code

### Job Enqueue (S2-W8-02)

When Haiku Call 1 completes and both async jobs are enqueued:

```python
# After analysis_ready event is fired and DB state is committed
def enqueue_async_jobs(analysis_id: str, form_analysis_row: dict):
    """Enqueue Haiku Call 2 and OpenCV Part 2 in parallel."""
    
    # Haiku Call 2 job
    haiku_job_id = queue_job(
        job_type="haiku_call_2",
        analysis_id=analysis_id,
        task_data={
            "user_id": form_analysis_row["user_id"],
            "exercise_id": form_analysis_row["exercise_id"],
            "biomechanics_json": form_analysis_row["biomechanics_json"],
            "coaching_output": form_analysis_row["coaching_output"],
            # ... other fields
        },
        timeout_seconds=120,
        max_retries=3
    )
    
    # Emit haiku_call_2_queued event
    emit_sse_event(
        event_type="haiku_call_2_queued",
        analysis_id=analysis_id,
        session_id=form_analysis_row["session_id"],
        user_id=form_analysis_row["user_id"],
        job_id=haiku_job_id,
        status="queued",
        estimated_completion_ms=15000  # typical: 12-18s
    )
    
    # OpenCV Part 2 job (parallel)
    opencv_job_id = queue_job(
        job_type="opencv_part_2",
        analysis_id=analysis_id,
        task_data={
            "user_id": form_analysis_row["user_id"],
            "video_url": form_analysis_row["video_url"],
            "biomechanics_json": form_analysis_row["biomechanics_json"],
            # ... other fields
        },
        timeout_seconds=60,
        max_retries=2
    )
    
    # Emit opencv_part_2_queued event
    emit_sse_event(
        event_type="opencv_part_2_queued",
        analysis_id=analysis_id,
        session_id=form_analysis_row["session_id"],
        user_id=form_analysis_row["user_id"],
        job_id=opencv_job_id,
        status="queued",
        estimated_completion_ms=8000  # typical: 6-10s
    )
```

### Job Started (S2-W8-04)

When job worker picks up task from queue:

```python
def on_job_started(job_id: str, job_type: str, analysis_id: str):
    """Fire SSE event when job execution begins."""
    
    form_analysis = db.query(FormAnalysis).filter_by(id=analysis_id).first()
    
    event_type = f"{job_type}_started"  # "haiku_call_2_started" or "opencv_part_2_started"
    
    emit_sse_event(
        event_type=event_type,
        analysis_id=analysis_id,
        session_id=form_analysis.session_id,
        user_id=form_analysis.user_id,
        job_id=job_id,
        status="running",
        started_at=datetime.utcnow().isoformat() + "Z"
    )
```

### Job Complete (S2-W8-04)

When job finishes successfully and output written to DB:

```python
def on_job_complete(job_id: str, job_type: str, analysis_id: str, job_output: dict):
    """Fire SSE event when job completes successfully."""
    
    form_analysis = db.query(FormAnalysis).filter_by(id=analysis_id).first()
    
    # Update DB with job output
    if job_type == "haiku_call_2":
        form_analysis.haiku_call_2_status = "complete"
        form_analysis.haiku_call_2_output = job_output
        form_analysis.haiku_call_2_completed_at = datetime.utcnow()
    elif job_type == "opencv_part_2":
        form_analysis.opencv_part_2_status = "complete"
        form_analysis.annotated_frame_url = job_output["frame_url"]
        form_analysis.opencv_part_2_completed_at = datetime.utcnow()
    
    db.session.commit()
    
    event_type = f"{job_type}_complete"  # "haiku_call_2_complete" or "opencv_part_2_complete"
    
    emit_sse_event(
        event_type=event_type,
        analysis_id=analysis_id,
        session_id=form_analysis.session_id,
        user_id=form_analysis.user_id,
        job_id=job_id,
        status="complete",
        completed_at=datetime.utcnow().isoformat() + "Z",
        **additional_fields_per_job_type(job_type, job_output)
    )
    
    # Additional fields for OpenCV only
    if job_type == "opencv_part_2":
        # Frame complete event includes signed URL
        event["annotated_frame_url"] = job_output["signed_url"]
```

### Job Failed (S2-W8-04)

When job fails after all retries exhausted:

```python
def on_job_failed(job_id: str, job_type: str, analysis_id: str, exception: Exception, attempt: int):
    """Fire SSE event when job fails after retries."""
    
    form_analysis = db.query(FormAnalysis).filter_by(id=analysis_id).first()
    
    # Map exception to error code
    error_code = map_exception_to_error_code(exception, job_type)
    
    # Determine if retryable
    retryable = should_retry(error_code, attempt, job_type)
    
    # Update DB with failure
    if job_type == "haiku_call_2":
        form_analysis.haiku_call_2_status = "failed"
        form_analysis.haiku_call_2_error = str(exception)
        form_analysis.haiku_call_2_completed_at = datetime.utcnow()
    elif job_type == "opencv_part_2":
        form_analysis.opencv_part_2_status = "failed"
        form_analysis.opencv_part_2_error = str(exception)
        form_analysis.opencv_part_2_completed_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log error with context
    logger.error(
        f"Job failed: {job_type}",
        extra={
            "job_id": job_id,
            "analysis_id": analysis_id,
            "error_code": error_code,
            "attempt": attempt,
            "exception": str(exception),
            "traceback": traceback.format_exc()
        }
    )
    
    # Emit job_failed event
    emit_sse_event(
        event_type="job_failed",
        analysis_id=analysis_id,
        session_id=form_analysis.session_id,
        user_id=form_analysis.user_id,
        job_id=job_id,
        job_type=job_type,
        status="failed",
        error_code=error_code,
        error_message=str(exception),  # Internal log, never shown to user
        retryable=retryable
    )

def map_exception_to_error_code(exception: Exception, job_type: str) -> str:
    """Convert Python exception to error_code enum."""
    
    if job_type == "haiku_call_2":
        if isinstance(exception, anthropic.APITimeoutError):
            return "HAIKU_CALL_2_TIMEOUT"
        elif isinstance(exception, json.JSONDecodeError):
            return "HAIKU_CALL_2_INVALID_OUTPUT"
        elif isinstance(exception, anthropic.BadRequestError) and "context_window" in str(exception):
            return "HAIKU_CALL_2_CONTEXT_OVERFLOW"
        elif isinstance(exception, anthropic.APIStatusError):
            return "HAIKU_CALL_2_API_ERROR"
        elif isinstance(exception, sqlalchemy.exc.SQLAlchemyError):
            return "HAIKU_CALL_2_DB_WRITE_ERROR"
        else:
            return "HAIKU_CALL_2_API_ERROR"  # default fallback
    
    elif job_type == "opencv_part_2":
        if isinstance(exception, cv2.error):
            # Distinguish between frame extraction and annotation
            if "bottom_timestamp" in str(exception) or "seek" in str(exception):
                return "FRAME_EXTRACTION_FAILED"
            else:
                return "ANNOTATION_FAILED"
        elif isinstance(exception, google.api_core.exceptions.GoogleAPICallError):
            return "OPENCV_GCS_WRITE_ERROR"
        elif isinstance(exception, sqlalchemy.exc.SQLAlchemyError):
            return "OPENCV_DB_WRITE_ERROR"
        elif isinstance(exception, TimeoutError):
            return "OPENCV_TIMEOUT"
        else:
            return "ANNOTATION_FAILED"  # default fallback
    
    return "SYSTEM_ERROR"

def should_retry(error_code: str, attempt: int, job_type: str) -> str:
    """Determine if job should be retried. Returns "true", "false", or "partial"."""
    
    # All OpenCV errors are non-blocking (Tab 1 visible)
    if job_type == "opencv_part_2":
        return "partial"
    
    # Haiku Call 2 errors are async (Tab 2 only affected)
    if job_type == "haiku_call_2":
        non_retryable_codes = {
            "HAIKU_CALL_2_INVALID_OUTPUT",
            "HAIKU_CALL_2_CONTEXT_OVERFLOW",
            "NO_PREVIOUS_SESSION"
        }
        if error_code in non_retryable_codes:
            return "false"
        else:
            # Retryable if not exhausted
            return "true" if attempt < 3 else "false"
    
    return "false"  # default: non-retryable
```

---

## Part 4: Error Message Lookup Table

Frontend uses this table to convert `error_code` to user-facing message. All errors belong to either Tab 1 (blocking) or Tab 2 (non-blocking).

### Tab 2 Errors (Haiku Call 2 — Non-blocking)

| error_code | retryable | User-facing message |
|---|---|---|
| `HAIKU_CALL_2_TIMEOUT` | `"partial"` | Progression data is taking longer than expected. Try tapping the tab again in a moment. |
| `HAIKU_CALL_2_INVALID_OUTPUT` | `"partial"` | We couldn't generate your progression data. Your form analysis above is complete and saved. |
| `HAIKU_CALL_2_CONTEXT_OVERFLOW` | `"partial"` | Your session history is too long for progression analysis. Form analysis remains complete. |
| `HAIKU_CALL_2_API_ERROR` | `"partial"` | Progression service temporarily unavailable. Try again in a moment. |
| `HAIKU_CALL_2_DB_WRITE_ERROR` | `"partial"` | Progression saved partially — analysis complete above. |
| `NO_PREVIOUS_SESSION` | `"false"` | This is your first session for this exercise — progression tracking will appear after your next upload. |

### Tab 1 Images (OpenCV Part 2 — Non-blocking)

| error_code | retryable | User-facing message |
|---|---|---|
| `FRAME_EXTRACTION_FAILED` | `"partial"` | We couldn't generate the form snapshot. Your coaching is still fully available above. |
| `ANNOTATION_FAILED` | `"partial"` | We couldn't generate the form snapshot. Your coaching is still fully available above. |
| `OPENCV_TIMEOUT` | `"partial"` | Form snapshot generation is taking longer — coaching available above. |
| `OPENCV_GCS_WRITE_ERROR` | `"partial"` | Form snapshot generated but couldn't be saved. Coaching analysis complete. |
| `OPENCV_DB_WRITE_ERROR` | `"partial"` | Form snapshot partially saved. Coaching analysis complete. |

---

## Part 5: Database Schema Fields (S2-W8-01 Reference)

These fields in `form_analysis_results` table support the async job tracking:

### Haiku Call 2 Job Tracking

```sql
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_status VARCHAR(20) DEFAULT 'queued';
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_queued_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_started_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_completed_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_output JSONB;
ALTER TABLE form_analysis_results ADD COLUMN haiku_call_2_error TEXT;
```

### OpenCV Part 2 Job Tracking

```sql
ALTER TABLE form_analysis_results ADD COLUMN opencv_part_2_status VARCHAR(20) DEFAULT 'queued';
ALTER TABLE form_analysis_results ADD COLUMN opencv_part_2_queued_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN opencv_part_2_started_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN opencv_part_2_completed_at TIMESTAMP;
ALTER TABLE form_analysis_results ADD COLUMN annotated_frame_url VARCHAR(2048);
ALTER TABLE form_analysis_results ADD COLUMN opencv_part_2_error TEXT;
```

---

## Part 6: Testing & Observability

### Manual Test Checklist

- [ ] Upload video, observe SSE stream in browser console
- [ ] Both `haiku_call_2_queued` and `opencv_part_2_queued` fire immediately after `analysis_ready`
- [ ] Both `_started` events fire within 2–5 seconds (job assigned to worker)
- [ ] `haiku_call_2_complete` fires within 12–18s after job start
- [ ] `opencv_part_2_complete` fires within 6–10s after job start
- [ ] On error: simulate timeout, catch exception, verify `job_failed` event emitted
- [ ] Verify Tab 2 shows loading state until `haiku_call_2_complete` or `job_failed`
- [ ] Verify Tab 1 image placeholder stays as placeholder if `opencv_part_2_complete` doesn't arrive

### Logging Requirements

Every job state change must log to CloudLogging:

```python
# Haiku Call 2
logger.info(f"Job haiku_call_2 queued: {haiku_job_id} for analysis {analysis_id}")
logger.info(f"Job haiku_call_2 started: {haiku_job_id}, processing session {analysis_id}")
logger.info(f"Job haiku_call_2 complete: {haiku_job_id}, progression_output stored")
logger.error(f"Job haiku_call_2 failed: {error_code}, analysis {analysis_id}, attempt {attempt}")

# OpenCV Part 2
logger.info(f"Job opencv_part_2 queued: {opencv_job_id} for analysis {analysis_id}")
logger.info(f"Job opencv_part_2 started: {opencv_job_id}, extracting frame from {analysis_id}")
logger.info(f"Job opencv_part_2 complete: {opencv_job_id}, frame uploaded to {gcs_url}")
logger.error(f"Job opencv_part_2 failed: {error_code}, analysis {analysis_id}, attempt {attempt}")
```

### Metrics to Instrument

- `haiku_call_2_latency_seconds` — time from queued → complete
- `opencv_part_2_latency_seconds` — time from queued → complete
- `haiku_call_2_retry_count` — how many retries before success/failure
- `opencv_part_2_retry_count` — how many retries before success/failure
- `job_failure_rate_by_error_code` — track which errors are most common

---

## Part 7: Frontend Integration Checklist

**Squad 1 must:**

- [ ] Listen for `haiku_call_2_queued` event → show "Generating recommendations..." in Tab 2
- [ ] Listen for `haiku_call_2_complete` event → unlock Tab 2, call `GET /analysis/{id}/progression`
- [ ] Listen for `opencv_part_2_queued` event → show loading state for image in Tab 1 (optional)
- [ ] Listen for `opencv_part_2_complete` event → swap image placeholder with `annotated_frame_url`
- [ ] Listen for `job_failed` event → handle based on `job_type` (Tab 1 or Tab 2)
- [ ] For `job_type: "haiku_call_2"` failures → show error message in Tab 2
- [ ] For `job_type: "opencv_part_2"` failures → show inline warning, but keep coaching text visible
- [ ] Implement retry logic for `retryable: "true"` errors
- [ ] Show "Try again" button only for `retryable: "true"`
- [ ] Never show `error_message` field to user — only use `error_code` to look up message
- [ ] Handle case where both jobs complete out-of-order (no assumptions about timing)
