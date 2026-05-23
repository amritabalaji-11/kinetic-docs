# Roadmap Visual Update — Handoff for Next Session

**Status:** Ready to sync Week 6 & 7 tasks from ClickUp files to roadmap_visual.html

## Files to Update
- **Source:** `/ClickUp Tasks/clickup_week6_tasks.html` + `Kinetic_W7_ClickUp_Tasks.html`
- **Target:** `Team Meeting (Not Technical)/roadmap_visual.html`

## What's Already Done
✅ Removed 16 outdated tasks (Nemotron/RAG era)
✅ Cleaned up Week 5 carry-overs

## What Needs Doing

### 1. Update Week 6 Milestone Badge
- **Current:** "1st E2E Slice + Nemotron Tests"
- **Should be:** "1st E2E Slice + Haiku A/B Test"
- **Location:** Line ~320

### 2. Remove Nemotron-Related Tasks (if still present)
- S2-W5-09 (NVIDIA NIM Nemotron)
- S2-W5-10 (Nemotron test plan)
- S2-W6-05 (Nemotron Tests A/B/C)

### 3. Sync Week 6 Tasks from ClickUp

**Squad 1 (8 tasks):**
- S1-W6-01: Design handoff — Homepage · Auth · Profile screens
- S1-W6-02: Build Upload screen — exercise selector, weight input, file upload, filming tips
- S1-W6-03: Wire SSE to real processing states
- S1-W6-04: Build Analysis Results screen — form score, joint corrections, coaching tips
- S1-W6-05: Build Dashboard shell — dummy session history + score trend
- S1-W6-06: History, Dashboard, Workout Logger — dummy data shells
- S1-W6-07: E2E slice — wire real /upload endpoint, render biomechanics JSON
- S1-W6-08: Pre-upload client-side validation

**Squad 2 (7 tasks):**
- S2-W6-P1: Integration meeting with Squad 3 — agree process_video() contract
- S2-W6-P2: Stitch full upload → pipeline → DB → SSE sequence
- S2-W6-01: Upgrade POST /upload (real fields, GCS path)
- S2-W6-02: Replace stub SSE with real pipeline events
- S2-W6-03: Store biomechanics → GET /analysis/{id}/result
- S2-W6-04: Quality gate error relay (M1–M6 codes)
- S2-W6-05: Model A/B Test — JSON vs frames vs video (compare for W7 architecture)

**Squad 3 (7 tasks):**
- S3-W6-P1: Expose process_video() as callable function
- S3-W6-P2: Gold standard data prep — run 3–5 videos through pipeline
- S3-W6-C1: Complete and commit OpenCV Python wrapper
- S3-W6-01: Complete MediaPipe pipeline — frame selection, quality gate
- S3-W6-02: Write biomechanics script — keypoints → angles
- S3-W6-03: Expose biomechanics output to Squad 2
- S3-W6-04: (RAG task — check if should be removed per Haiku shift)

### 4. Add Week 7 Tasks from Kinetic_W7_ClickUp_Tasks.html

Extract all S1-W7, S2-W7, S3-W7 tasks and populate Week 7 column

**Key change:** Week 7 should reflect Haiku 4.5 + no RAG (not Nemotron/RAG)

### 5. Update References to Nemotron/RAG in descriptions
- S2-W7-02: Update from "Nemotron output" to "Haiku Call 1 output"
- S2-W8-06: Remove nemotron error codes, add Haiku-specific codes
- S3-W9-02: Update from "RAG refinement" to "prompt refinement"

## Quick Extract Command (for next session)
```bash
# Get all Week 6 task IDs from ClickUp
grep -o "S[0-9]-W6-[A-Z0-9]*" /Users/amrit/Documents/projects/Kinetic/ClickUp\ Tasks/clickup_week6_tasks.html | sort | uniq

# Get all Week 7 task IDs from ClickUp
grep -o "S[0-9]-W7-[A-Z0-9]*" /Users/amrit/Documents/projects/Kinetic/ClickUp\ Tasks/Kinetic_W7_ClickUp_Tasks.html | sort | uniq
```

## Architecture Context
- **W6 A/B test result:** Haiku 4.5 selected (better coaching quality)
- **Nemotron removed:** From all pipelines
- **RAG removed:** Coaching files injected directly in system prompt (no vector DB)
- **Auth deferred:** Using 3 hardcoded demo user IDs for demo day

---
**Last updated:** May 24, 2026 | **Status:** Ready for fresh session sync
