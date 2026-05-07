# Kinetic — Squad Roadmap: Weeks 5–10
**May 4 – June 8, 2026**

---

## Squads

| Squad | Members | Focus |
|-------|---------|-------|
| **Squad 1 — Frontend** | Designers + 1.5 FE Devs + 1 PM | Responsive web app, UX, SSE, dummy-data-first |
| **Squad 2 — Backend** | 1.5 PM + 2 BE Devs | Upload pipeline, MediaPipe, Nemotron, Claude Sonnet, structured DB |
| **Squad 3 — Data / Full Stack** | 1.5 PM + 1.5 Data Scientists + 1 Full Stack | RAG ingestion, vector DB, retrieval quality |

---

## Integration Rhythm

- **Thursday each week:** All squads merge to `main` on GitHub — working code only, no WIP
- **Goal:** Surface integration issues early; never save all squad connections for the final weeks
- **First thin E2E slice:** End of Week 6 — all three squads' work touches for the first time

---

## Dependency Map

| Dependency | From | To | Due |
|-----------|------|----|-----|
| Agreed JSON response schema (form analysis output) | Squad 2 | Squad 1 (dummy data shape) | Thu Week 5 |
| Agreed SSE event contract (processing states) | Squad 1 | Squad 2 (event names + payload) | Thu Week 5 |
| Vector DB seeded + queryable (Goblet Squat) | Squad 3 | Squad 2 (RAG calls) | Thu Week 6 |
| `/analyze` endpoint (video → biomechanics JSON) | Squad 2 | Squad 1 (replace dummy data) | Thu Week 6 |
| Auth endpoints (sign up / login) | Squad 2 | Squad 1 (onboarding screens go live) | Thu Week 7 |
| Full pipeline (Nemotron → RAG → Claude Sonnet output) | Squad 2 + 3 | Squad 1 (results screen goes real) | Thu Week 7 |
| Progression recommendation endpoint | Squad 2 | Squad 1 (weight recommendation UI) | Thu Week 8 |
| Accuracy validation results (20–30 videos) | Squad 3 | Squad 2 (prompt/RAG refinement) | Thu Week 9 |

---

## Week 5 — May 4–8 | Foundation & Contracts

**Theme:** Scaffold everything. Agree on all shared contracts before building. No squad should be blocked by another after this week.

### Squad 1 — Frontend
- [ ] Scaffold React + Tailwind project, confirm folder structure and component conventions
- [ ] Define and document **JSON schema for all frontend-consumed responses** (form analysis result, auth, workout log, SSE events) — share with Squad 2 for alignment
- [ ] Build dummy data fixtures matching agreed JSON schema
- [ ] Scaffold core screen shells: Upload, Results, Dashboard, History, Workout Logger, Onboarding
- [ ] Implement **SSE skeleton** on Upload screen — define processing states (e.g. `uploading`, `analysing`, `generating_coaching`, `complete`, `error`) and render placeholder UI for each state
- [ ] Agree SSE event names + payloads with Squad 2
- [ ] **[Design]** Upload flow screens → Form Analysis results screens (wireframes ready for dev handoff by Thu)

**Thursday merge:** React scaffold + dummy data + SSE state skeleton + agreed JSON contracts committed

---

### Squad 2 — Backend
- [ ] Provision GCP project, S3/Cloud Storage buckets, API Gateway
- [ ] Scaffold Python API project structure (routes, services, models)
- [ ] Define and agree **biomechanics output JSON format** with Squad 1 and Squad 3 (joint angles, rep count, rep time, stability, posture — all typed and versioned)
- [ ] Scope MediaPipe integration for Goblet Squat: identify required keypoints, joint angle computations, rep segmentation approach
- [ ] Define structured DB schema: `users`, `sessions`, `exercises`, `workout_logs` (exercise, sets, reps, weight), `form_scores` — share with Squad 3
- [ ] Stub `/upload` and `/analyze` endpoints (accept video, return hardcoded biomechanics JSON) so Squad 1 can start integrating
- [ ] **[S2-W5-09 — NEW ⚠️ URGENT]** Provision NVIDIA NIM API access for Nemotron 3 Nano Omni — confirm hello world call from Python backend, document multimodal input format (video + JSON), record response time. Must complete by Thu — blocks all W6 Nemotron work
- [ ] **[S2-W5-10 — NEW]** Define Nemotron input test plan (Scenarios A, B, C) — write test scripts + sample JSON, confirm joint overlay video is in correct format. Execute in W6 parallel track

**Thursday merge:** GCP infra live + API scaffold + stubbed endpoints + schema docs + Nemotron API confirmed + test plan committed

---

### Squad 3 — Data / Full Stack
- [ ] Collect 20–30 high-quality RAG sources for Goblet Squat: research papers, YouTube transcripts, Kaggle datasets, Instagram tutorials, biomechanics references, muscle anatomy images
- [ ] Define **vector DB schema**: document structure, metadata fields (exercise, source type, confidence level, angle parameters), embedding strategy
- [ ] Define **structured DB schema** (coordinate with Squad 2 — single source of truth)
- [ ] Evaluate and select vector DB (e.g. Pinecone, Weaviate, pgvector) — document rationale
- [ ] Define ingestion pipeline architecture: chunking strategy, embedding model, metadata tagging

**Thursday merge:** Source list documented + vector DB + structured DB schemas agreed + ingestion architecture decision committed

---

## Week 6 — May 11–17 | Build Core + First Thin E2E Slice

**Theme:** Each squad builds their core feature. By Thursday, all three squads connect for the first time — upload a real video, get real biomechanics data back on the frontend.

### Squad 1 — Frontend
- [ ] Build **Upload screen** (full): exercise selector, weight input field, video file upload, filming tips modal
- [ ] Wire SSE to real processing states — test against Squad 2's stub endpoint
- [ ] Build **Analysis Results screen** using dummy data: form score, joint angle corrections, coaching tips, weight recommendation (placeholder)
- [ ] Build **Dashboard shell** with dummy session history and score trend chart
- [ ] **End of week:** Replace Upload dummy data with real `/upload` endpoint — first real video upload working in browser
- [ ] **[Design]** Home Screen + Authentication screens (wireframes ready for dev handoff by Thu)
- [ ] **[Design]** Dashboard & Profile screens (wireframes ready for dev handoff by Thu)

**Thursday merge (E2E slice):** Upload → real endpoint → MediaPipe biomechanics JSON → displayed on Results screen (even if Nemotron/Claude not wired yet)

---

### Squad 2 — Backend

**Main track — MediaPipe completion:**
- [ ] Implement **video upload endpoint**: receive video, store to GCS, return upload confirmation + SSE stream
- [ ] Complete **MediaPipe pipeline**: frame selection logic + video quality gate (bad angle / joint undetectable → retake message to user)
- [ ] Write **biomechanics script**: convert raw MediaPipe keypoints → knee angle, hip angle, rep count, rep time, tempo (using parameters from PT-01 Phase 1)
- [ ] Return structured **biomechanics JSON** from `/analyze` endpoint
- [ ] Emit correct **SSE events** at each pipeline stage

**Parallel track — Nemotron input testing (S2-W5-10 execution):**
- [ ] **Test A:** Joint overlay video only → Nemotron → record output quality + response time
- [ ] **Test B:** Biomechanics JSON only → Nemotron → record output quality + response time
- [ ] **Test C:** Both inputs together → Nemotron → record output quality + response time
- [ ] Log comparison findings: which combination gives best output? does video add meaningful value over JSON alone?
- [ ] **Feed findings to PM** — informs final pipeline architecture before W7 full build

**Thursday merge (E2E slice):** Upload video → video stored in GCS → MediaPipe runs → biomechanics JSON returned → SSE events firing → Squad 1 renders real data on Results screen. Nemotron test results committed alongside.

---

### Squad 3 — Data / Full Stack
- [ ] **Ingest Goblet Squat corpus** into vector DB: chunk documents, generate embeddings, store with metadata
- [ ] Implement and test **RAG retrieval**: given a biomechanics query (e.g. "knee angle 142° at bottom of squat"), retrieve top-k relevant passages
- [ ] Validate retrieval quality manually: check that top results are relevant and grounded (not generic fitness content)
- [ ] Expose **RAG retrieval endpoint** for Squad 2 to call

**Thursday merge:** Vector DB seeded + RAG retrieval endpoint live + retrieval quality spot-checked

---

## Week 7 — May 18 | Connect the Full Pipeline

**Theme:** Wire the complete AI pipeline end-to-end. First full form analysis session — real video in, real coaching output out.

### Squad 1 — Frontend
- [ ] **Replace all dummy data** on Results screen with real pipeline output (Nemotron + Claude Sonnet coaching)
- [ ] Build **Onboarding / Sign-up screen**: account creation, exercise preferences, training frequency
- [ ] Build **Workout Logger screen**: log sets, reps, weight; link to form session
- [ ] Update Dashboard to reflect real session data once auth lands
- [ ] Build **History screen**: list of past sessions with form score trend line
- [ ] **[Design]** Subpages from Profile + Onboarding screens (wireframes ready for dev handoff by Thu)
- [ ] **[Design]** Workout Builder & Tracker screens (wireframes ready for dev handoff by Thu)

**Thursday merge:** Results screen live with real coaching output; Onboarding + History screens committed

---

### Squad 2 — Backend
- [ ] Complete **Nemotron 3 Nano Omni integration**: raw video + biomechanics JSON → structured JSON output + word-level timestamps + chain-of-thought paragraphs
- [ ] On Nemotron output generated: **call Squad 3's RAG endpoint** with relevant biomechanics context
- [ ] Query **structured DB**: retrieve user's weight history and past form sessions for current exercise
- [ ] Pass Nemotron output + RAG results + user history + current weight → **Claude Sonnet** for coaching and progression recommendation
- [ ] Return full coaching response to frontend via SSE
- [ ] Implement **authentication** (sign up, login, JWT): protect all user-specific endpoints

**Thursday merge:** Full pipeline live (video → MediaPipe → Nemotron → RAG + DB → Claude Sonnet → coaching output); auth endpoints working

---

### Squad 3 — Data / Full Stack
- [ ] **Enhance RAG corpus**: add audio transcripts from form videos, muscle anatomy images, additional biomechanics edge cases
- [ ] Refine retrieval: tune chunking, re-rank results, improve relevance for joint-angle-specific queries
- [ ] Begin defining **good/bad Goblet Squat scenarios** for sample video testing (target 20–30 videos for Week 9 validation)
- [ ] Stress-test RAG endpoint under concurrent requests (Squad 2 will call this in the pipeline)

**Thursday merge:** Enhanced corpus ingested + retrieval refinement committed + sample video scenario definitions documented

---

## Week 8 — May 25 | Progression Logic, Workout Tracker & Prototype Screens

**Theme:** Complete the longitudinal layer — progression recommendations, workout logging, full auth flow. Finalize prototype screens for final design sign-off.

### Squad 1 — Frontend
- [ ] Wire **auth flow**: onboarding/sign-up screen connects to real auth endpoints; session persistence
- [ ] Complete **Workout Planner / Tracker**: log workout entries, link to form analysis sessions
- [ ] Surface **weight-based progression recommendation** prominently on Results screen ("Your form at 12kg is solid — you're ready for 14kg")
- [ ] Finalize **prototype screens** — all screens review-ready for design sign-off
- [ ] Responsive design pass: ensure all screens are mobile-friendly
- [ ] Begin filming tips screen (guidance on camera angle, distance, lighting for MediaPipe accuracy)

**Thursday merge:** Auth flow live; workout tracker wired; progression recommendation displayed; prototype screens finalized

---

### Squad 2 — Backend
- [ ] Implement **progression recommendation logic**: compare current session form scores against past sessions at same/lower weights; output `ready_to_progress` / `hold` / `drop_weight` with reasoning
- [ ] Complete **workout logging endpoints**: create/read workout entries, associate with form sessions
- [ ] Implement **user history query**: return all past form sessions for an exercise with weights and scores
- [ ] Refine prompt engineering for Claude Sonnet: improve coaching language, ensure recommendations are specific and actionable
- [ ] Harden error handling: what happens if MediaPipe fails to detect keypoints, Nemotron times out, RAG returns no results

**Thursday merge:** Progression logic live; workout logging endpoints working; Claude Sonnet prompt refinements committed

---

### Squad 3 — Data / Full Stack
- [ ] **Collect sample test videos** (Goblet Squat): 20–30 videos with defined good/bad form scenarios
- [ ] Label ground truth for each video (expected form scores, joint corrections) for Week 9 validation
- [ ] Refine ingestion pipeline: add more Goblet Squat RAG sources if retrieval gaps found
- [ ] Test full RAG-to-Claude-Sonnet flow: does retrieval context meaningfully improve coaching quality vs. no RAG?

**Thursday merge:** Sample video test set ready (labeled); RAG ingestion refined; integration test results documented

---

## Week 9 — June 1 | Accuracy Validation & Performance

**Theme:** Validate everything. Hit the accuracy and latency targets. Refine until the product is launch-ready.

### Squad 1 — Frontend
- [ ] Complete **filming tips screen**: in-app guidance before upload (camera angle, distance, lighting, clothing)
- [ ] Polish **SSE experience**: smooth progress indicators, clear state messaging at each pipeline stage
- [ ] Final mobile responsiveness pass across all screens
- [ ] Bug fixes from internal testing
- [ ] If capacity: implement **"Record" option** on Upload screen (alongside "Upload from file")

**Thursday merge:** Filming tips live; SSE UX polished; mobile responsive; record option if complete

---

### Squad 2 — Backend
- [ ] **End-to-end latency optimisation**: profile pipeline, identify bottlenecks, target <30s upload-to-results
- [ ] Refine **prompt engineering** based on accuracy validation findings from Squad 3
- [ ] Implement **confidence thresholding**: flag low-certainty outputs ("we couldn't confidently analyse this video — try these filming tips") rather than returning unreliable results
- [ ] Load test API endpoints; fix any stability issues

**Thursday merge:** Latency <30s validated; confidence thresholding live; load test results documented

---

### Squad 3 — Data / Full Stack
- [ ] Run **accuracy validation**: test pipeline on 20–30 labeled sample videos
- [ ] Measure: form score agreement with expert labels (target ≥80%), rep count accuracy (target ≥90%), joint correction relevance
- [ ] Document failures and edge cases — feed findings back to Squad 2 for prompt/RAG refinement
- [ ] Final RAG refinement pass based on validation gaps

**Thursday merge:** Accuracy validation report committed; ≥80% expert agreement confirmed or refinements in progress

---

## Week 10 — June 8 | UAT, E2E Testing & Final Pitch Prep

**Theme:** Harden, validate with real users, prepare to ship and present.

### All Squads
- [ ] **UAT**: run end-to-end user acceptance testing with real test users (VOC participants if available)
- [ ] **E2E test suite**: cover critical paths — sign up → upload video → view results → log workout → view history → progression recommendation
- [ ] Fix all high and medium severity bugs surfaced in UAT
- [ ] Verify all **launch criteria** from PRD are checked off
- [ ] Confirm metrics instrumentation: session uploads, form score events, SSE completion, weekly retention tracking
- [ ] **Final pitch preparation**: demo video, slide deck, live demo rehearsal

### Squad 1 — Frontend
- [ ] Final UI polish pass
- [ ] Confirm all screens match approved design prototype
- [ ] Verify filming tips are clear and effective (test with non-technical users)

### Squad 2 — Backend
- [ ] Confirm all endpoints stable under expected load
- [ ] Privacy/data handling check: video storage, retention policy
- [ ] Final pipeline smoke test

### Squad 3 — Data / Full Stack
- [ ] Final RAG retrieval quality check
- [ ] Confirm vector DB performance under load
- [ ] Document RAG corpus and ingestion pipeline for handoff

**Thursday merge / Release candidate:** All squads green. Launch criteria met.

---

## Launch Criteria Checklist (from PRD)

- [ ] Goblet Squat analysis pipeline working end-to-end
- [ ] ≥80% expert agreement on form scoring (20–30 test videos)
- [ ] Weight-based progression recommendation validated
- [ ] End-to-end latency <30 seconds
- [ ] All P0 features complete
- [ ] Design prototype approved
- [ ] UAT passed
- [ ] Metrics instrumented
- [ ] Filming guidelines live in-app
- [ ] Zero high-severity bugs in E2E test suite
- [ ] Privacy policy in place for video data

---

## Weekly Milestone Summary

| Week | Dates | Milestone |
|------|-------|-----------|
| **5** | May 4–8 | All scaffolds live. JSON contracts agreed. Schemas defined. No squad blocked. |
| **6** | May 11–17 | **First thin E2E slice:** Real video upload → MediaPipe → biomechanics JSON → displayed on frontend. RAG queryable. |
| **7** | May 18–24 | **Full pipeline live:** Nemotron + RAG + Claude Sonnet coaching output on screen. Auth working. |
| **8** | May 25–31 | Progression recommendations live. Workout tracker wired. Auth flow complete. Prototype screens final. |
| **9** | Jun 1–7 | Accuracy ≥80% validated. Latency <30s. Confidence thresholding. Record option if capacity. |
| **10** | Jun 8 | UAT + E2E testing complete. Launch criteria all green. Final pitch ready. |

---

*Last updated: May 4, 2026*
