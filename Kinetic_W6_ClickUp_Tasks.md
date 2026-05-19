# Kinetic AI — Week 6 ClickUp Tasks
**Sprint:** Week 6 — May 11–17
**Goal:** Build core features across all squads. By Thursday, all three squads connect for the first time — real video upload → MediaPipe biomechanics JSON → displayed on Results screen.

---

## 🟦 Squad 1 — Frontend

---

**[S1-W6-01] Upload Screen — Full Build**
- **Status:** To Do
- **Priority:** High
- **Description:** Build the full Upload screen: exercise selector, weight input field, video file upload, and filming tips modal.

---

**[S1-W6-02] Wire SSE to Real Processing States**
- **Status:** To Do
- **Priority:** High
- **Description:** Connect SSE skeleton to real processing states. Test against Squad 2's stub endpoint. Ensure all states (uploading, analysing, generating_coaching, complete, error) render correctly.

---

**[S1-W6-03] Analysis Results Screen — Dummy Data**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Build the Analysis Results screen using dummy data: form score, joint angle corrections, coaching tips, weight recommendation (placeholder).

---

**[S1-W6-04] Dashboard Shell**
- **Status:** ✅ Done
- **Priority:** Medium
- **Description:** Build Dashboard shell with dummy session history and score trend chart.

---

**[S1-W6-05] Replace Dummy Data — Real Upload Endpoint**
- **Status:** To Do
- **Priority:** High
- **Description:** End-of-week milestone. Replace Upload screen dummy data with real `/upload` endpoint — first real video upload working in browser.
- **Dependency:** S2-W6-04

---

**[S1-W6-D01] [Design] Homepage · Authentication · Profile · User Profile**
- **Status:** To Do
- **Priority:** High
- **Assignee:** Designer
- **Description:** Wireframes for Homepage, Authentication, Profile, and User Profile screens ready for dev handoff by Thursday.

---

**Thursday merge target (E2E slice):** Upload → real endpoint → MediaPipe biomechanics JSON → displayed on Results screen (even if Haiku not wired yet)

---

## 🟩 Squad 2 — Backend

### Main Track — MediaPipe Completion

---

**[S2-W6-01] Video Upload Endpoint**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Implement the video upload endpoint: receive video, store to GCS, return upload confirmation + SSE stream.

---

**[S2-W6-02] MediaPipe Pipeline — Complete**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Frame selection logic + video quality gate. Bad angle or undetectable joints → retake message returned to user.

---

**[S2-W6-03] Biomechanics Script**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Convert raw MediaPipe keypoints → knee angle, hip angle, rep count, rep time, tempo. Uses parameters from PT-01 Phase 1.

---

**[S2-W6-04] Structured Biomechanics JSON — `/analyze` Endpoint**
- **Status:** 🔄 In Progress
- **Priority:** High
- **Description:** Return structured biomechanics JSON from the `/analyze` endpoint. This is the output Squad 1 consumes to render the Results screen.
- **Blocks:** S1-W6-05, S2-W6-P2

---

**[S2-W6-05] SSE Events**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Emit correct SSE events at each pipeline stage so Squad 1's processing states update in real time.

---

### Parallel Track — Nemotron Input Testing

---

**[S2-W6-P1] Test A — Joint Overlay Video Only → Nemotron**
- **Status:** ✅ Done
- **Priority:** Medium
- **Description:** Send joint overlay video only to Nemotron. Record output quality and response time.

---

**[S2-W6-P2] Tests B + C + Findings → PM**
- **Status:** 🔄 In Progress
- **Priority:** Medium
- **Description:** Complete remaining Nemotron input tests and surface findings to PM.
  - **Test B:** Biomechanics JSON only → Nemotron → record output quality + response time
  - **Test C:** Both inputs together → Nemotron → record output quality + response time
  - Log comparison: which combination gives best output? Does video add meaningful value over JSON alone?
  - Feed findings to PM — informs final pipeline architecture before W7 full build
- **Note:** Will close when S2-W6-04 is done.

---

**Thursday merge target (E2E slice):** Upload video → stored in GCS → MediaPipe runs → biomechanics JSON returned → SSE events firing → Squad 1 renders real data on Results screen. Nemotron test results committed alongside.

---

## 🟧 Squad 3 — Data / Full Stack

---

**[S3-W6-P1] Ingest Goblet Squat Corpus**
- **Status:** ✅ Done
- **Priority:** High
- **Description:** Chunk Goblet Squat source documents, generate embeddings, store in vector DB with metadata.

---

**[S3-W6-01] RAG Retrieval — Implement + Test**
- **Status:** To Do
- **Priority:** High
- **Description:** Given a biomechanics query (e.g. "knee angle 142° at bottom of squat"), retrieve top-k relevant passages. Test end-to-end retrieval.
- **Dependency:** S3-W6-P1

---

**[S3-W6-02] Validate Retrieval Quality**
- **Status:** To Do
- **Priority:** High
- **Description:** Manually spot-check top retrieval results — confirm they are biomechanics-relevant and not generic fitness content.

---

**[S3-W6-03] RAG Retrieval Endpoint — Expose to Squad 2**
- **Status:** To Do
- **Priority:** High
- **Description:** Expose the RAG retrieval endpoint so Squad 2 can call it as part of the Haiku prompt assembly in W7.
- **Blocks:** S2-W7-04

---

**Thursday merge target:** Vector DB seeded + RAG retrieval endpoint live + retrieval quality spot-checked

---

## 📋 Carryover from Week 5 — In Progress

| Task ID | Squad | Status |
|---------|-------|--------|
| S3-W5-01 | Squad 3 | 🔄 In Progress |
| S3-W5-08 | Squad 3 | 🔄 In Progress |

---

## ✅ Week 6 Progress Summary

| Squad | Done | In Progress | To Do |
|-------|------|-------------|-------|
| Squad 1 | S1-W6-03, S1-W6-04 | — | S1-W6-01, S1-W6-02, S1-W6-05, S1-W6-D01 |
| Squad 2 | S2-W6-01, S2-W6-02, S2-W6-03, S2-W6-05, S2-W6-P1 | S2-W6-04, S2-W6-P2 | — |
| Squad 3 | S3-W6-P1 | — | S3-W6-01, S3-W6-02, S3-W6-03 |
