# Kinetic — Squad Roadmap: Weeks 5–10
**May 4 – June 8, 2026**
*Last updated: May 18, 2026*

---

## Squads

| Squad | Members | Focus |
|-------|---------|-------|
| **Squad 1 — Frontend** | Designers + 1.5 FE Devs + 1 PM | Responsive web app, UX, SSE, dummy-data-first |
| **Squad 2 — Backend** | 1.5 PM + 2 BE Devs | Upload pipeline, MediaPipe, Claude Haiku 4.5, structured DB |
| **Squad 3 — Data / Full Stack** | 1.5 PM + 1.5 Data Scientists + 1 Full Stack | Gold standard data, MediaPipe pipeline, synthetic user data, accuracy validation |

---

## Architecture Decisions (confirmed)

> - **Nemotron → Claude Haiku 4.5** — A/B test concluded Haiku handles analysis + coaching end-to-end. Nemotron removed from all pipelines.
> - **Vector DB + ingestion pipeline scrapped** — No vector DB, no embedding pipeline. Coaching context delivered via gold standard JSON + session history + direct .md file retrieval in Haiku prompt.
> - **Authentication → Demo user IDs** — Full Google OAuth / JWT deferred post-demo. 3 hardcoded user IDs used for all W7 pipeline testing and demo day.

---

## Integration Rhythm

- **Thursday each week:** All squads merge to `main` on GitHub — working code only, no WIP
- **Goal:** Surface integration issues early; never save all squad connections for the final weeks
- **First thin E2E slice:** End of Week 6 — all three squads' work touches for the first time

---

## Dependency Map

| Dependency | From | To | Due | Status |
|-----------|------|----|-----|--------|
| Agreed JSON response schema (form analysis output) | Squad 2 | Squad 1 (dummy data shape) | Thu W5 | ✅ |
| Agreed SSE event contract (processing states) | Squad 1 | Squad 2 (event names + payload) | Thu W5 | ✅ |
| `/analyze` endpoint (video → biomechanics JSON) | Squad 2 | Squad 1 (replace dummy data) | Thu W6 | 🟠 In Progress |
| Demo user IDs configured + queryable | Squad 2 | Squad 1 (profile selector) | Thu W7 | — |
| Full pipeline (Haiku 4.5 analysis + coaching output) | Squad 2 + 3 | Squad 1 (results screen goes real) | Thu W7 | — |
| Progression recommendation endpoint | Squad 2 | Squad 1 (weight recommendation UI) | Thu W8 | — |
| Accuracy validation results (20–30 videos) | Squad 3 | Squad 2 (prompt refinement) | Thu W9 | — |

---

## Week 5 — May 4–8 | Foundation & Contracts ✅ Complete

**Theme:** Scaffold everything. Agree on all shared contracts before building. No squad should be blocked by another after this week.

### Squad 1 — Frontend
- ✅ Scaffold React + Tailwind project, confirm folder structure and component conventions
- ✅ Define and document **JSON schema for all frontend-consumed responses** (form analysis result, workout log, SSE events) — share with Squad 2 for alignment
- ✅ Build dummy data fixtures matching agreed JSON schema
- ✅ Scaffold core screen shells: Upload, Results, Dashboard, History, Workout Logger, Onboarding
- ✅ Implement **SSE skeleton** on Upload screen — define processing states (`uploading`, `analysing`, `generating_coaching`, `complete`, `error`) and render placeholder UI for each state
- ✅ Agree SSE event names + payloads with Squad 2
- ✅ **[Design]** Upload video → Processing → Form Analysis screens (wireframes ready for dev handoff)

**Thursday merge:** ✅ React scaffold + dummy data + SSE state skeleton + agreed JSON contracts committed

---

### Squad 2 — Backend
- ✅ Provision GCP project, Cloud Storage buckets, API Gateway
- ✅ Scaffold Python API project structure (routes, services, models)
- ✅ Define and agree **biomechanics output JSON format** with Squad 1 and Squad 3 (joint angles, rep count, rep time, stability, posture — all typed and versioned)
- ✅ Scope MediaPipe integration for Goblet Squat: identify required keypoints, joint angle computations, rep segmentation approach
- ✅ Define structured DB schema: `users`, `sessions`, `exercises`, `workout_logs`, `form_scores` — share with Squad 3
- ✅ Stub `/upload` and `/analyze` endpoints (accept video, return hardcoded biomechanics JSON) so Squad 1 can start integrating
- ✅ **[S2-W5-09]** Provision NVIDIA NIM API access for Nemotron — confirmed API access, documented multimodal input format *(Nemotron subsequently replaced by Haiku 4.5 following W6 A/B test)*
- ✅ **[S2-W5-10]** Define LLM input test plan (Scenarios A, B, C) — write test scripts + sample JSON. Executed in W6 parallel track → informed Haiku decision

**Thursday merge:** ✅ GCP infra live + API scaffold + stubbed endpoints + schema docs committed

---

### Squad 3 — Data / Full Stack
- ✅ Define **structured DB schema** (coordinate with Squad 2 — single source of truth)
- ✅ Collect Goblet Squat reference sources (research papers, biomechanics references, coaching transcripts)
- ~~Define **vector DB schema**: document structure, metadata fields, embedding strategy~~ — *Scrapped: RAG ingestion dropped*
- ~~Evaluate and select vector DB (Pinecone, Weaviate, pgvector)~~ — *Scrapped: RAG ingestion dropped*
- ~~Define ingestion pipeline architecture: chunking strategy, embedding model, metadata tagging~~ — *Scrapped: RAG ingestion dropped*
- 🟠 **[S3-W5-01]** *(Carried into W7)* — In Progress
- 🟠 **[S3-W5-08]** *(Carried into W7)* — In Progress

**Thursday merge:** ✅ Structured DB schema agreed + reference sources documented

---

## Week 6 — May 11–17 | Build Core + First Thin E2E Slice

**Theme:** Each squad builds their core feature. By Thursday, all three squads connect for the first time — upload a real video, get real biomechanics data back on the frontend.

### Squad 1 — Frontend
- [ ] Build **Upload screen** (full): exercise selector, weight input field, video file upload, filming tips modal `[S1-W6-01]`
- [ ] Wire SSE to real processing states — test against Squad 2's stub endpoint `[S1-W6-02]`
- ✅ Build **Analysis Results screen** using dummy data: form score, joint angle corrections, coaching tips, weight recommendation (placeholder) `[S1-W6-03]`
- ✅ Build **Dashboard shell** with dummy session history and score trend chart `[S1-W6-04]`
- [ ] **End of week:** Replace Upload dummy data with real `/upload` endpoint — first real video upload working in browser `[S1-W6-05]`
- [ ] **[Design]** Homepage · Profile · User Profile screens (wireframes ready for dev handoff by Thu) `[S1-W6-D01]`

**Thursday merge (E2E slice):** Upload → real endpoint → MediaPipe biomechanics JSON → displayed on Results screen

---

### Squad 2 — Backend

**Main track — MediaPipe completion:**
- ✅ Implement **video upload endpoint**: receive video, store to GCS, return upload confirmation + SSE stream `[S2-W6-01]`
- ✅ Complete **MediaPipe pipeline**: frame selection logic + video quality gate (bad angle / joint undetectable → retake message to user) `[S2-W6-02]`
- ✅ Write **biomechanics script**: convert raw MediaPipe keypoints → knee angle, hip angle, rep count, rep time, tempo `[S2-W6-03]`
- 🟠 Return structured **biomechanics JSON** from `/analyze` endpoint `[S2-W6-04]`
- ✅ Emit correct **SSE events** at each pipeline stage `[S2-W6-05]`

**Parallel track — LLM input A/B test (informs W7 architecture):**
- ✅ **Test A:** Joint overlay video only → Nemotron → output quality + response time recorded `[S2-W6-P1]`
- 🟠 **Tests B + C + findings → PM** — JSON only, both inputs; log comparison; feed to PM `[S2-W6-P2 — closes with S2-W6-04]`
- *Outcome: Haiku 4.5 selected. Nemotron dropped. Vector DB ingestion dropped — coaching content retrieved directly from .md files.*

**Thursday merge (E2E slice):** Upload video → GCS → MediaPipe → biomechanics JSON → SSE firing → Squad 1 renders real data

---

### Squad 3 — Data / Full Stack
- ✅ **Goblet Squat corpus collected** and reference materials documented `[S3-W6-P1]`
- ~~Implement and test **RAG retrieval**~~ — *Scrapped: RAG ingestion dropped* `[S3-W6-01]`
- ~~Validate retrieval quality manually~~ — *Scrapped: RAG ingestion dropped* `[S3-W6-02]`
- ~~Expose **RAG retrieval endpoint** for Squad 2~~ — *Scrapped: RAG ingestion dropped* `[S3-W6-03]`

**Thursday merge:** Corpus documented + structured DB confirmed

---

## Week 7 — May 18–24 | Connect the Full Pipeline

**Theme:** Wire the complete AI pipeline end-to-end with Haiku 4.5 as the core model. First full form analysis session — real video in, real coaching output with longitudinal context out.

> **Architecture (confirmed):** OpenCV extracts 8-frame composite grid. Haiku 4.5 receives: MediaPipe JSON + 8 frames + gold standard reference JSON + last 3 user sessions + coaching language from .md files → returns structured coaching output. No Nemotron. No vector DB. Auth deferred — 3 demo user IDs used.

### Squad 1 — Frontend
- [ ] **Form analysis 1st cut** — wire Results screen to real Haiku output: verdict, total score (/100), positive observations, critical observations (root cause / symptom tagging), recommendation, rep trend
- [ ] **Home screen + Login page** — scaffold and build home/dashboard; login page shows 3 demo user profile selector (no real auth)
- [ ] **[Design handoff]** Form Comparison & Progression screen — review and finalise wireframes; handed off to dev by end of week
- [ ] **[Design]** Workout Builder & Logger — design begins; not expected to complete this week

**Thursday merge:** Results screen live with real Haiku output · Home screen committed · Design handoffs delivered

---

### Squad 2 — Backend
- [ ] **Integrate Claude Haiku 4.5** — single call handles full analysis + coaching output; Nemotron removed entirely
- [ ] **Gold standard query** — query Supabase gold standard squat table for elite trainer reference JSON; include in Haiku prompt
- [ ] **User session history query** — pull last 3 sessions for demo user + exercise: weight, MediaPipe JSON, coaching output; pass as longitudinal context
- [ ] **Coaching content retrieval** — retrieve relevant coaching language from curated .md files; include in Haiku prompt. No vector DB — direct file-based retrieval
- [ ] **Assemble Haiku prompt** — combine: current 8-frame composite + MediaPipe JSON + weight + gold standard JSON + 3-session history + coaching .md content → call Haiku → return structured coaching output
- [ ] **SSE delivery** — return Haiku coaching response via SSE; update processing states for new multi-step pipeline
- [ ] **Demo user setup** — create 3 hardcoded user IDs; scope all pipeline queries to these users; full Google OAuth / JWT deferred post-demo

**Thursday merge:** Full pipeline live (video → OpenCV + MediaPipe → Haiku prompt → coaching output via SSE) · Demo users queryable

#### Schema + Contract Patches (W7 — must complete before pipeline wiring)
- [ ] **[PATCH-S2-W7-A] DB schema migration — `form_analysis_results`**
  - **ADD:** `range_of_motion_score` (int) · `rep_scores` (jsonb) · `faults_detected` (jsonb) · `confidence` (jsonb) · `causal_chain` (jsonb) · `fault_detail` (jsonb — key field for longitudinal progression) · `trends` (jsonb) · `annotated_frame_url` (string, nullable) · `progression_output` (jsonb, nullable)
  - **REMOVE:** `nemotron_output_url` · `chain_of_thought` · `annotated_frames_urls` (array) · `issues_json` · `progression_recommendation` (enum)
- [ ] **[PATCH-S2-W7-B] SSE event contract update** — retire: `nemotron_started/complete`, `overlay_complete`, `frames_extracting/ready`, `rag_started/complete`, `claude_started/complete`, `analysis_complete`. Add: `haiku_started`, `analysis_ready`, `frame_ready`, `progression_ready`. Update `FE_SSE_and_Errors.md` + `FE_Response_Schemas.md` to match.
- [ ] **[PATCH-S2-W7-C] Haiku Call 2 async endpoint** — implement `GET /analysis/{id}/progression` endpoint; returns `progression_output` JSON (Section 1 + Section 2) from `form_analysis_results`.

---

### Squad 3 — Data / Full Stack
- [ ] **MediaPipe pipeline update** — (1) refine angle calculations from A/B test findings; (2) update OpenCV wrapper to 8-frame composite grid extraction (replaces full video overlay); (3) add `session_valgus_fault` boolean to `consolidated.stability` — ≥50% of valid reps with `knee_valgus_distance < 0.22`
- [ ] **Gold standard table** — run MediaPipe on elite trainer goblet squat videos; store biomechanics JSON in Supabase gold standard table (same schema as user session output). Minimum 2–3 reference videos for W7 testing
- [ ] **Coaching .md files — curate and organise** — finalise coaching content files used for retrieval; ensure content covers key fault patterns for Goblet Squat. No vector DB or embedding pipeline
- [ ] **Synthetic user data** — seed a test user ID with 3 past sessions (weight + MediaPipe JSON + Haiku coaching output per session) to validate longitudinal feedback flow before real user data exists
- [ ] **Visual output scoping** — prototype and compare 3 options: (1) annotated worst-rep bottom frame, (2) 5–8s slow-motion clip around fault moment, (3) full processed video with skeleton overlay. No build decision — scope, test, present recommendation
- 🟠 **[S3-W5-01]** Carry-over from W5 — In Progress
- 🟠 **[S3-W5-08]** Carry-over from W5 — In Progress

#### Biomechanics Schema Patches (W7 — required for OpenCV Part 2)
- [ ] **[PATCH-S3-W7-A] Add `bottom_frame` + `bottom_timestamp_ms` to biomechanics JSON per rep** — frame index and timestamp (ms) at the squat bottom position. Required by OpenCV Part 2 to seek the correct frame. Without these, worst-rep frame extraction cannot function.
- [ ] **[PATCH-S3-W7-B] Add `session_valgus_fault` to `consolidated.stability`** — boolean: `true` if ≥50% valid reps have `knee_valgus_distance < 0.22`. Makes valgus detection deterministic in the pipeline rather than relying on LLM.

**Thursday merge:** MediaPipe updated · ≥2 gold standard records in Supabase · Synthetic user data seeded · Visual output options documented

---

## Week 8 — May 25–31 | Progression Logic, Workout Tracker & Prototype Screens

**Theme:** Complete the longitudinal layer — progression recommendations, workout logging. Finalise prototype screens for design sign-off.

### Squad 1 — Frontend
- [ ] **Demo user profile selector** — user picks from 3 demo profiles on login screen; session scoped to selected user ID
- [ ] **Profile screen build** — full build of Profile screen; design handed off from W7
- [ ] **[Design handoff]** Profile + Onboarding screens — wireframes finalised and handed off to dev
- [ ] Complete **Workout Planner / Tracker**: log workout entries, link to form analysis sessions
- [ ] Surface **weight-based progression recommendation** on Results screen ("Your form at 12kg is solid — you're ready for 14kg")
- [ ] Finalise **prototype screens** — all screens review-ready for design sign-off
- [ ] Responsive design pass across all screens
- [ ] Begin filming tips screen (camera angle, distance, lighting guidance)

**Thursday merge:** Demo profile selector live · Workout tracker wired · Progression recommendation displayed · Prototype screens finalised

---

### Squad 2 — Backend
- [ ] Implement **progression recommendation logic**: compare current session scores against past sessions; output `ready_to_progress` / `hold` / `drop_weight` with reasoning
- [ ] Complete **workout logging endpoints**: create/read workout entries, associate with form sessions
- [ ] Implement **user history query**: return all past form sessions for an exercise with weights and scores
- [ ] Refine **Haiku prompt engineering**: improve coaching language specificity and actionability based on W7 output review
- [ ] Harden error handling: MediaPipe keypoint detection failure, Haiku timeout, no session history available

**Thursday merge:** Progression logic live · Workout logging endpoints working · Haiku prompt refinements committed

---

### Squad 3 — Data / Full Stack
- [ ] **Collect sample test videos** (Goblet Squat): 20–30 videos with defined good/bad form scenarios
- [ ] Label ground truth for each video (expected form scores, joint corrections) for W9 validation
- [ ] Validate visual output decision from W7 scoping — confirm format to build in W9

**Thursday merge:** Test video set ready (labelled) · Visual output format confirmed

---

## Week 9 — June 1–7 | Accuracy Validation & Performance

**Theme:** Validate everything. Hit accuracy and latency targets. Refine until the product is launch-ready.

### Squad 1 — Frontend
- [ ] Complete **filming tips screen**: in-app guidance before upload
- [ ] Polish **SSE experience**: smooth progress indicators, clear state messaging at each pipeline stage
- [ ] Final mobile responsiveness pass across all screens
- [ ] Bug fixes from internal testing
- [ ] If capacity: implement **"Record" option** on Upload screen (alongside "Upload from file")

**Thursday merge:** Filming tips live · SSE UX polished · Mobile responsive · Record option if complete

---

### Squad 2 — Backend
- [ ] **End-to-end latency optimisation**: profile pipeline, identify bottlenecks, target <30s upload-to-results
- [ ] Refine **Haiku prompt engineering** based on accuracy validation findings from Squad 3
- [ ] Implement **confidence thresholding**: flag low-certainty outputs ("we couldn't confidently analyse this video — try these filming tips") rather than returning unreliable results
- [ ] Load test API endpoints; fix any stability issues

**Thursday merge:** Latency <30s validated · Confidence thresholding live · Load test results documented

---

### Squad 3 — Data / Full Stack
- [ ] Run **accuracy validation**: test pipeline on 20–30 labelled sample videos
- [ ] Measure: form score agreement with expert labels (target ≥80%), rep count accuracy (target ≥90%), joint correction relevance
- [ ] Document failures and edge cases — feed findings to Squad 2 for prompt refinement
- [ ] Validate visual output in-app with internal testers

**Thursday merge:** Accuracy validation report committed · ≥80% expert agreement confirmed or refinements in progress

---

## Week 10 — June 8 | UAT, E2E Testing & Final Pitch Prep

**Theme:** Harden, validate with real users, prepare to ship and present.

### All Squads
- [ ] **UAT**: end-to-end user acceptance testing with real test users
- [ ] **E2E test suite**: cover critical paths — select demo profile → upload video → view results → log workout → view history → progression recommendation
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
- [ ] Final accuracy spot-check on pipeline
- [ ] Confirm gold standard table is complete and queryable
- [ ] Document MediaPipe pipeline and gold standard setup for handoff

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

| Week | Dates | Milestone | Status |
|------|-------|-----------|--------|
| **5** | May 4–8 | All scaffolds live. JSON contracts agreed. Schemas defined. No squad blocked. | ✅ Complete |
| **6** | May 11–17 | **First thin E2E slice:** Real video upload → MediaPipe → biomechanics JSON → displayed on frontend. | 🟠 In Progress |
| **7** | May 18–24 | **Full pipeline live:** Haiku 4.5 analysis + coaching output on screen. Demo user IDs working. | — |
| **8** | May 25–31 | Progression recommendations live. Workout tracker wired. Prototype screens final. | — |
| **9** | Jun 1–7 | Accuracy ≥80% validated. Latency <30s. Confidence thresholding. Record option if capacity. | — |
| **10** | Jun 8 | UAT + E2E testing complete. Launch criteria all green. Final pitch ready. | — |
