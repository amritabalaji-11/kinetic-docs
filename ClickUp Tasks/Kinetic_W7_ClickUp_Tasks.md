# Kinetic AI — Week 7 ClickUp Tasks
**Sprint:** Week 7 — May 18–24  
**Goal:** Wire the complete AI pipeline end-to-end with Claude Haiku 4.5. First real coaching output with longitudinal context.  
**Architecture note:** Nemotron replaced by Claude Haiku 4.5. Full auth deferred — 3 demo user IDs used instead.

---

## 🟦 Squad 1 — Frontend

---

**[S1-W7-01] Form Analysis Results — 1st Cut**
- **Status:** To Do
- **Priority:** High
- **Description:** Wire the Results screen to real Haiku output. Replace all dummy data with live response from the pipeline.
- **Output schema to implement:**
  - `verdict` — 2–3 sentence summary (always visible)
  - `total_score` — /100
  - `positive_observations` — up to 3, with category tag
  - `critical_observations` — up to 3, ordered by severity, with root cause / symptom tag
  - `recommendation` — what to do in the next session
  - `rep_trend` — observation + 1-line recommendation

---

**[S1-W7-02] Home Screen Build + Login Page Build**
- **Status:** To Do
- **Priority:** High
- **Description:** Scaffold and build the home/dashboard screen. Build the login page with user profile selection — show 3 demo user profiles for selection (no real auth, just profile picker tied to demo user IDs from Squad 2).

---

**[S1-W7-03] Start Build — Profile & Login Screen**
- **Status:** To Do
- **Priority:** Medium
- **Description:** Initial scaffolding and component structure for the Profile & Login screen. Full build continues in W8.

---

**[S1-W7-04] [Design] Profile + Onboarding Screens — Dev Handoff**
- **Status:** To Do
- **Priority:** High
- **Assignee:** Designer
- **Description:** Finalise wireframes for Profile and Onboarding user screens. Hand off to dev by end of week.

---

**[S1-W7-05] [Design] Workout Builder & Logger — Design Begins**
- **Status:** To Do
- **Priority:** Medium
- **Assignee:** Designer
- **Description:** Design work begins on Workout Builder & Logger screens. Not expected to complete this week — continues into W8.

---

**Thursday merge target:** Results screen live with real Haiku coaching output · Home screen committed · Design handoffs delivered

---

## 🟩 Squad 2 — Backend

---

**[S2-W7-01] Replace Nemotron with Claude Haiku 4.5**
- **Status:** To Do
- **Priority:** High
- **Description:** Remove Nemotron 3 Nano Omni integration entirely. Claude Haiku 4.5 takes over analysis + coaching in a single call. Update all references in the pipeline.
- **Dependency:** Squad 3 MediaPipe pipeline update (S3-W7-01)

---

**[S2-W7-02] Gold Standard Query**
- **Status:** To Do
- **Priority:** High
- **Description:** Query Supabase gold standard squat table for elite trainer reference biomechanics JSON (same MediaPipe schema as user session). Include in Haiku prompt as reference for direct angle comparison.
- **Dependency:** Squad 3 gold standard table populated (S3-W7-02)

---

**[S2-W7-03] User Session History Query**
- **Status:** To Do
- **Priority:** High
- **Description:** Pull the last 3 sessions for the current user + exercise from DB. For each session retrieve: weight used, MediaPipe JSON output, and Haiku coaching output. Pass all 3 as longitudinal context in the Haiku prompt.

---

**[S2-W7-04] RAG Retrieval**
- **Status:** To Do
- **Priority:** High
- **Description:** Retrieve relevant coaching language from indexed .md files and transcribed coaching text. Include retrieved context in the Haiku prompt for coaching language grounding.
- **Dependency:** Squad 3 RAG corpus indexed (S3-W7-03)

---

**[S2-W7-05] Assemble Haiku Prompt + Call**
- **Status:** To Do
- **Priority:** High
- **Description:** Combine all inputs into a single structured prompt and call Haiku:
  - Current 8-frame composite (from Squad 3 OpenCV output)
  - Current session MediaPipe JSON
  - Current session weight
  - Gold standard reference JSON
  - Last 3 sessions (weight + MediaPipe JSON + coaching output)
  - RAG coaching context
  - → Call Claude Haiku 4.5
  - → Return structured coaching output (verdict, score, positives, criticals, recommendation, rep trend)
- **Dependency:** S2-W7-01, S2-W7-02, S2-W7-03, S2-W7-04

---

**[S2-W7-06] SSE Delivery**
- **Status:** To Do
- **Priority:** High
- **Description:** Return Haiku coaching response to frontend via SSE. Update SSE processing states to reflect the new multi-step pipeline (uploading → extracting frames → running MediaPipe → fetching context → generating coaching → complete).

---

**[S2-W7-07] Demo User Setup**
- **Status:** To Do
- **Priority:** High
- **Description:** Create 3 hardcoded user IDs for demo day. Scope all pipeline queries (session history, weight, coaching history) to these 3 users. Full Google OAuth / JWT authentication deferred to post-demo.

---

**Thursday merge target:** Full pipeline live (video → MediaPipe → multi-source prompt → Haiku → SSE output) · Demo users working

---

## 🟧 Squad 3 — Data / Full Stack

---

**[S3-W7-01] MediaPipe Pipeline Update**
- **Status:** To Do
- **Priority:** High
- **Description:** Two updates to the MediaPipe pipeline:
  1. **JSON angles** — validate and refine angle calculations based on A/B test findings (e.g. dorsiflexion numeric + classification, valgus threshold alignment). Update output schema where needed.
  2. **OpenCV wrapper** — edit script from full video overlay output to 8-frame composite grid extraction. This is the format validated with Haiku in the A/B test and becomes the LLM visual input going forward.
- **Blocks:** S2-W7-01, S2-W7-05

---

**[S3-W7-02] Gold Standard Table — Supabase**
- **Status:** To Do
- **Priority:** High
- **Description:** Run MediaPipe on elite trainer goblet squat videos. Store resulting biomechanics JSON in the Supabase gold standard squat table using the same schema as user session output. Minimum 2–3 reference videos for W7 testing.
- **Blocks:** S2-W7-02

---

**[S3-W7-03] RAG Corpus — Index Coaching Content**
- **Status:** To Do
- **Priority:** High
- **Description:** Index coaching .md files and transcribed coaching text into the RAG pipeline. Tune retrieval for biomechanics and form correction queries. Expose retrieval endpoint for Squad 2 to call.
- **Blocks:** S2-W7-04

---

**[S3-W7-04] Synthetic User Data**
- **Status:** To Do
- **Priority:** High
- **Description:** Seed a test user ID with 3 past sessions to validate the longitudinal feedback pipeline end-to-end. Each session must include:
  - Weight used
  - MediaPipe JSON biomechanics output
  - Haiku coaching output (can be generated from existing test data)
- Used by Squad 2 to test the session history query before real user data exists.
- **Blocks:** S2-W7-03

---

**[S3-W7-05] Visual Output Scoping**
- **Status:** To Do
- **Priority:** Medium
- **Description:** Prototype and compare 3 options for the form analysis visual shown to the user:
  1. Annotated worst-rep bottom frame (static image)
  2. 5–8 second slow-motion video clip around the key fault moment
  3. Full processed video with skeleton overlay (10fps, already generated by MediaPipe)
  
  **No build decision this week.** Scope effort, test each option, and present to the team with a recommendation before W8.

---

**Thursday merge target:** MediaPipe pipeline updated · Gold standard table populated · RAG corpus indexed · Synthetic user data seeded · Visual output options documented

---

## ✅ Thursday Merge Checklist

| Squad | Done when... |
|---|---|
| Squad 1 | Results screen renders real Haiku output · Home + Login screen committed · Design handoffs delivered |
| Squad 2 | Full pipeline fires end-to-end for at least 1 demo user ID · SSE events firing correctly |
| Squad 3 | MediaPipe updated · ≥2 gold standard records in Supabase · RAG endpoint returning results · Synthetic user data queryable |
