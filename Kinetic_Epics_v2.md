# Kinetic — Epics & User Stories v2
**Version:** v2 · Revised scope post mentor review  
**Date:** May 2026  
**Exercise scope:** Goblet Squat (MVP)  
**Demo format:** No auth — 2–3 hardcoded demo users, user selected via dropdown on Upload screen

---

## Product Context

Kinetic is an AI-powered form coaching app. Users upload a video of themselves doing an exercise, and Kinetic analyses their technique rep-by-rep using computer vision + AI, then delivers personalised coaching and a weight progression recommendation.

**Core pipeline:** User uploads video → MediaPipe (joint detection) → Biomechanics script → OpenCV (skeleton overlay) → ~~Nemotron~~ → **Haiku 4.5** (form scoring) → ~~Claude Sonnet~~ → **Claude Haiku 4.5 — Call 2** *(W6 A/B test)* (coaching) → Results screen

**What makes it different:** Per-rep scoring across a full set, longitudinal tracking across sessions, weight-specific coaching, and a worst-rep annotated frame showing the user their own body position with joint angles overlaid.

---

## MVP Scope Summary

| Area | Decision |
|---|---|
| Exercise | Goblet Squat only |
| Auth | Dropped — 2–3 hardcoded demo users, dropdown selector |
| RAG | Simplified — 5–10 MD coaching files in Claude system prompt (no Vector DB) |
| Gold standard | 3–5 good-form reference videos → `gold_standard_biomechanics` DB table |
| Profile screen | Frontend shell only — no backend endpoints |
| Onboarding | Dropped (auth dropped → no onboarding entry point) |

---

## Epics → User Stories

---

### E1 — Identity & Access `DROPPED`

**Original outcome:** I can log in and my sessions persist to my account  
**Status:** Dropped for demo. Replaced by demo user selector dropdown.

**Why dropped:** Auth adds significant Squad 1 + Squad 2 build effort with zero demo value. Hardcoded user IDs enable switching between demo users on the dashboard, which is more compelling than a single user account.

#### ~~US-01 — Sign In~~ `Dropped`
#### ~~US-03 — Returning User Login~~ `Dropped`

---

#### US-01b — Demo User Selection (Proxy Auth Entry Screen) `New`
**Week:** W7

> As a demo user entering the app, I want to select which user I am from a simple entry screen, so that the app loads the right session history and progression data for that user.

**Design note:** This is the first screen when opening the app. Shows 2–3 named demo users with a brief description (e.g. "Alex — 3 sessions, progressing at 12kg"). Designed to look and feel like a login/profile selector — a clear, intentional placeholder for the real auth flow post-demo. The selected `user_id` is stored in the app session and passed as a header on all API requests.

**Acceptance Criteria:**
- Given I open the app, the first screen I see is a user selection screen — not the Upload screen or Dashboard directly
- Given the selection screen, I see 2–3 demo user cards, each showing a name and a one-line description of their training context
- Given I select a user, I am taken to the Dashboard with that user's session history, form score trend, and workout logs loaded
- Given a user is selected, their `user_id` is stored in the app session and sent as a header on all subsequent API requests
- Given I want to switch users, I can return to this screen to select a different demo user without reloading the app
- The screen is clearly styled as a stand-in for auth — framed in the demo as "in production this would be a login screen"

---

### E2 — The Analysis Core `UPDATED`

**Outcome:** I upload a video and get actionable coaching on my form  
**Weeks:** W6 (first cut) → W7 (complete)

**Key changes from v1:**
- RAG vector DB → replaced by MD files in Claude system prompt
- Squad 2 owns /upload, SSE, ~~Nemotron~~ → **Haiku 4.5**, Claude. Squad 3 owns MediaPipe, OpenCV, Biomechanics.
- Gold Standard data prep added (PT-02) — 3–5 reference videos → DB, used by OpenCV overlay + Claude prompt

---

#### US-04 — Video Submission `Updated`
**Week:** W6

> As a user ready to analyse my form, I want to select my exercise, enter my weight, and upload a video, so that Kinetic can analyse my session.

**POST /upload fields:** `video` (file) · `exercise_id` = "ex_gob_squat_001" · `weight_value` (float) · `weight_unit` = "kg"

**Acceptance Criteria:**
- Given I'm on the Upload screen, I see an inline filming guide — a reference image and 3–4 tips on camera angle, distance, height, and clothing (always visible, not a modal)
- Given I'm on the Upload screen, I can select an exercise (Goblet Squat for MVP)
- Given I've selected an exercise, I can enter the weight I used
- Given I tap to upload, my device's native file picker opens
- Given I select a video, I see the filename confirmed
- Given the file is unsupported or too large, I see a clear inline error
- Given all fields are complete, the Submit button becomes active
- Given I tap Submit, I'm taken to the processing screen

---

#### US-05 — Analysis Processing & Quality Gate Errors `Updated`
**Week:** W6

> As a user who just submitted a video, I want to see a clear processing status and — if my video is rejected — an error message that tells me exactly what went wrong and how to fix it.

**Processing:**
- Given I've submitted a video, I see a progress indicator with stage labels (e.g. "Reading your movement patterns…", "Analysing your form…") and a progress bar advancing per SSE event
- Given processing completes, I'm automatically taken to the Results screen

**Quality gate rejections — contextual error messages (specific per rejection reason):**
- Given video rejected for **bad angle** → "We couldn't detect your joints clearly — try filming from a 45° side angle so your full body is visible"
- Given video rejected for **poor visibility** → "Your joints were obscured — try wearing fitted clothing and filming in a well-lit space"
- Given video rejected for **partial occlusion** → "Part of your body was cut off — step back so your full body from head to toe is in frame"
- Given video rejected for **too few reps** → "We need at least 3 complete reps to analyse your form — film a longer set"
- Given any rejection, a "Try again" button returns to the Upload screen with filming tips visible

---

#### US-06a — Form Analysis Results Screen `Updated`
**Week:** W6 (dummy data) → W7 (real pipeline output)

> As a user who just had my form analysed, I want to see a clear breakdown of my performance, so that I understand what I'm doing well and what to work on.

**Screen layout and data sources:**

**Session context row:**
- Exercise Name — from DB (`exercises.display_name`)
- Date — `created_at` of current `analysis_id`
- Weight — `weight_value` + `weight_unit` from DB

**Visual proof:**
- Single annotated image — worst-rep bottom-position frame with skeleton lines, joint markers (colour-coded), and actual angles vs gold standard overlaid. `annotated_frame_url` from OpenCV → DB.

**Overall score:**
- Form score /100 — `summary.overall_form_score` from ~~Nemotron~~ → **Haiku 4.5**

**Personalised summary:**
- 1–2 sentence summary combining form quality + weight lifted — `coaching.summary_paragraph` from Claude
- e.g. "At 12kg your posture holds well across all reps, but your ankle dorsiflexion limits your depth from rep 5 onwards."

**4 Parameters — Posture · Stability · Movement Quality · Tempo:**
Each parameter shows:
- Score /100 — from ~~Nemotron~~ → **Haiku 4.5** (`summary.posture_score`, `summary.stability_score`, `summary.movement_quality_score`, `summary.tempo_score`)
- What they're doing well — affirmation sentence from Claude (`coaching.parameters.[x].affirmation`) — **W7/8 iteration, null in W6**
- What's off — specific observation from Claude (`coaching.parameters.[x].observation`) — **W7/8 iteration, null in W6**
- Action to work on — 1 concrete correction from Claude (`coaching.parameters.[x].correction`)

**Rep-by-rep score chart:**
- x-axis: rep number · y-axis: form score /100
- Data: `reps[n].rep_number` + `reps[n].form_score` from ~~Nemotron~~ → **Haiku 4.5**
- Performance Over Reps %: calculated frontend — `(score of highest rep − score of last rep) ÷ score of highest rep`

**Acceptance Criteria:**
- Given analysis is complete, I see a consolidated form score /100 prominently at the top
- Given the Results screen, I see the annotated worst-rep frame with skeleton overlay and joint angle labels
- Given the Results screen, I see 4 parameter sections each showing score /100 and 1 actionable correction
- Given the Results screen, I see a rep-by-rep score chart across the set
- Given I'm on mobile web, all sections are scannable without horizontal scrolling

---

#### US-06b — Visual Joint Overlay (Worst-Rep Annotated Frame) `Updated`
**Week:** W7

> As a user reviewing my results, I want to see an annotated image of my worst rep at the bottom position, so that I can see exactly what my body was doing at the most critical moment.

**Scope (Option 3 — confirmed):** Skeleton lines + joint markers + actual angles vs gold standard text

**Acceptance Criteria:**
- Given analysis is complete, I see an extracted frame from my worst-rep bottom position on the Results screen
- Given the frame, skeleton lines and joint markers show my body position — joint dots colour-coded: green (in range), amber (borderline), red (outside range)
- Given each joint, I see my actual angle and the gold standard range (e.g. "Knee: 88° · Ideal: 80–95°")
- Given I'm on mobile web, the frame is full-width and labels are legible without zooming

---

#### US-07 — AI Coaching Output `Updated`
**Week:** W7

> As a user who has received form analysis, I want personalised coaching that references my weight and history, so that the advice feels specific to me — not generic.

**Acceptance Criteria:**
- Given analysis is complete, I see minimum 2 specific joint-level corrections (e.g. "Ankle dorsiflexion limits depth from rep 5 onwards")
- Given each correction, I see at least 1 actionable coaching tip explaining how to fix it
- Given multiple sessions exist at different weights, coaching references my weight history (e.g. "Your form at 12kg has held for 3 sessions — ready for 14kg")
- Given results are detailed, they are scannable in under 10 seconds — score and recommendation first, details below

---

#### PT-02 — Gold Standard Data Prep `New (Product Task)`
**Week:** W6 data prep → W7 integrated into pipeline

3–5 good-form Goblet Squat reference videos run through MediaPipe + Biomechanics script. Outputs stored in `gold_standard_biomechanics` table. Serves two purposes:
1. Grounds Claude's coaching with real biomechanics reference data
2. Powers the angle comparison overlay in OpenCV Part 2 (actual vs ideal ranges)

**Acceptance Criteria:**
- 3–5 gold standard videos identified and agreed by PM before end of W6
- Videos processed through MediaPipe + Biomechanics pipeline — outputs stored in `gold_standard_biomechanics` table
- Reference angle ranges confirmed: knee (80–95° at bottom), hip (80–95°), ankle dorsiflexion (≥25°)
- OpenCV Part 2 can query `gold_standard_biomechanics` to retrieve reference values for overlay
- Gold standard values available in DB for Claude system prompt injection by W7

---

### E3 — Longitudinal Intelligence `UPDATED`

**Outcome:** I can see if I'm improving — and whether I'm ready to go heavier  
**Week:** W8

**Architecture change:** Weight history (past sessions, weights, form scores) retrieved from `workout_logs` DB and passed to ~~Claude Sonnet~~ → **Claude Haiku 4.5 — Call 2** *(W6 A/B test)* — not ~~Nemotron~~ → **Haiku 4.5**. ~~Nemotron~~ → **Haiku 4.5** analyses the current video only. Claude synthesises the progression recommendation using ~~Nemotron~~ → **Haiku 4.5**'s output + historical context. Cleaner separation: ~~Nemotron~~ → **Haiku 4.5** = form analysis this session, Claude = coaching + progression using history.

---

#### US-08 — Form Comparison & Progression Recommendation `Updated`
**Week:** W8

> As a user who has logged multiple sessions, I want to compare my current form against my last session and get a weight progression recommendation, so that I can see whether I'm improving and whether to go heavier.

**Form comparison screen layout:**

**a) Exercise Name** — from DB

**b) Left side — Current Analysis:**
- Date (`created_at`) · Weight (`weight_value` + `weight_unit`) — from DB
- Visual Proof — `annotated_frame_url` of current analysis (OpenCV → DB)
- Form Score /100 — `summary.overall_form_score` from ~~Nemotron~~ → **Haiku 4.5** output

**c) Right side — Previous Analysis** (most recent completed analysis for same `exercise_id` + `user_id`, resolved by backend):
- Date (`created_at`) · Weight (`weight_value` + `weight_unit`) — from DB
- Visual Proof — `annotated_frame_url` of previous analysis — from DB
- Form Score /100 — `summary.overall_form_score` of previous analysis — from Claude output

**d) Personalised comparison summary:**
- 1–2 sentences — `comparison_coaching.summary_paragraph` from Claude

**e) 4 Parameters — Posture · Stability · Movement Quality · Tempo:**
Each parameter shows:
- Score of current analysis with variance vs previous (e.g. 73 **+6**) — score from DB, variance calculated frontend (current minus previous)
- 1–2 sentence observation + action verdict — `comparison_coaching.parameters.[x].observation_action` from Claude

**f) Rep-by-rep score chart — current vs previous overlaid:**
- x-axis: rep number · y-axis: form score /100
- Two lines: current analysis + previous analysis (both from DB)
- Performance Over Reps %: calculated frontend — `(Σ current rep scores − Σ previous rep scores) ÷ Σ previous rep scores × 100`

**Case 2 — No previous session:**
- Show: "Sorry you do not have any past form analysis done before this session. Try the next time you do a form analysis"

**Acceptance Criteria:**
- Given I'm on the Results screen, I see a "Form Comparison" toggle
- Given I tap the toggle and have a previous session, I see the side-by-side view as described above
- Given I tap the toggle and have no previous session, I see the Case 2 message
- Given the comparison, I see parameter variance (+ or −) vs previous session
- Given multiple sessions exist, the progression recommendation (ready / hold / drop) references specific past sessions by weight

---

#### PT-01 — Progression Recommendation Logic Definition `Product Task`
**Week:** W5–W9

PM + Physical Trainer define the exact ruleset for "Ready to progress" / "Hold" / "Drop weight" before Squad 2 builds the logic in W8.

**4-Phase Delivery:**
- Phase 1 (W5 — done): Biomechanics parameters defined + ~~Nemotron~~ → **Haiku 4.5** output schema agreed
- Phase 2 (W7): Refine thresholds against first real pipeline output
- Phase 3 (Mon W8): Final spec to Squad 2 — exact thresholds, edge cases, three recommendation strings
- Phase 4 (W9): PT expert validation on 3–5 test videos including gold standard videos

---

### E4 — Habit & Engagement Loop `UPDATED`

**Outcome:** I come back because I can see my progress  
**Weeks:** W7–W8

**Change from v1:** Dashboard seeded with 3–4 pre-loaded sessions per demo user instead of real auth sessions. Demo operator uses the dropdown on Upload screen to switch users and show different progression stories (one user with improving form, one with degrading form at higher weights).

---

#### US-09 — Dashboard — Progression History `Updated`
**Week:** W7–W8

> As a user, I want my home screen to show a snapshot of my progress over time, so that I can see the longitudinal story of my training and stay motivated.

**Acceptance Criteria:**
- Given I land on the Dashboard, I see a form score trend chart across recent sessions
- Given the chart, I can see how form score changes as weight increases across sessions
- Given the dashboard, I see a session history list with exercise, date, weight, and overall score per session
- Given I tap a past session, I see the full Results screen for that session including the worst-rep annotated frame
- Given I'm on the Dashboard, I see a prominent "Analyse new session" CTA linking to the Upload screen
- Given I'm on mobile web, all sections are scannable without horizontal scrolling

---

#### US-10 — Session History
**Week:** W7

> As a user reviewing my progress, I want to see a chronological list of my past sessions, so that I can revisit specific sessions and track how I've progressed.

**Acceptance Criteria:**
- Given I'm in the History tab, I see all sessions in reverse-chronological order — each showing exercise name, date, weight, and overall form score
- Given I tap a past session, I see the full Results screen for that session
- Given I have no sessions, I see an empty state with a prompt to upload

---

### E5 — Workout Lifecycle `KEPT`

**Outcome:** I plan and log my workout in one place, linked to my form sessions  
**Week:** W8

**Note on scope:** Workout Logger reduced to frontend with dummy data for demo. No backend endpoints. This feeds the progression recommendation logic — workout logs are the source of historical weight + form data that feeds Claude's weight progression reasoning. Backend wired post-demo.

---

#### US-11a — Workout Builder
**Week:** W8

> As a user planning my workout, I want to quickly build a workout plan by selecting exercises, so that I know what I'm doing before I start training.

**Acceptance Criteria:**
- Given I'm in the Workout Builder, I see a list of exercises to choose from
- Given I select an exercise, it is added to my workout plan and I can specify target sets
- Given my workout plan is ready, I see a summary before starting

---

#### US-11b — Workout Tracker
**Week:** W8

> As a user mid-workout, I want to track my actual reps and weight per set as I go, so that my real performance is logged against my plan.

**Acceptance Criteria:**
- Given I complete a set, I can input my actual reps and weight and tap "Save" to confirm it is logged
- Given I've completed all sets, my workout is saved and linked to my session history
- Given I uploaded a form analysis in the same session, the workout log and form analysis are linked in History

---

### E6 — Personalization `UPDATED`

**Outcome (v1):** ~~Kinetic knows my body — frontend only in MVP, not wired to AI coaching~~  
**Outcome (v2):** Profile screen — frontend shell only. No backend. No onboarding (auth dropped).

**Epic-level change:** Auth dropped → no onboarding flow. Profile screen exists as a frontend shell (routable, shows dummy data, looks complete). No backend endpoints. Shown in demo as a design decision — personalisation wired to AI coaching is post-demo.

---

#### ~~US-02 — Injury & Pain Onboarding~~ `Dropped`
Dropped — auth removed → no onboarding flow. Can be added post-demo when auth is implemented.

---

#### US-12a — Training Preferences — Frontend Shell `Shell only`
**Week:** W8

> As a user, I want to see a training preferences section in my Profile, so that the product feels complete and personalisation is clearly designed for a future version.

**Scope:** Frontend shell only. Preferences screen exists and is routable. Displays dummy data. No save functionality. No backend endpoints.

---

#### US-12b — Injury & Pain Profile — Frontend Shell `Shell only`
**Week:** W8

> As a user, I want to see an injury and pain section in my Profile, so that I understand Kinetic plans to personalise coaching around my body in a future version.

**Scope:** Frontend shell only. Section visible in Profile. Displays placeholder. No backend. No edit functionality wired.

---

## Weekly Delivery View

| Week | Dates | Theme | Epics |
|---|---|---|---|
| W5 | May 4–8 | ✓ Finished — Scaffold + Contracts | — |
| W6 | May 11–17 | Thin E2E Slice + Data Prep | E2 partial |
| W7 | May 18–24 | Full Pipeline | E2 complete, E4 shell |
| W8 | May 25–31 | Differentiation + Lifecycle | E3, E4 complete, E5, E6 shell |
| W9 | Jun 1–7 | Validation | — |
| W10 | Jun 8 | UAT + Launch Criteria | — |

### Week 5 — ✓ Finished
**Theme:** Scaffold everything, agree all shared contracts. No squad blocked going into W6.

- **Squad 1:** React + Tailwind deployed to Vercel · JSON response schema defined · Dummy data fixtures built · Screen shells scaffolded · Upload screen started
- **Squad 2:** GitHub + GCP + Cloud Run deployed · DB schema + Supabase · Stub endpoints live · Nemotron API confirmed
- **Squad 3:** OpenCV wrapper · MediaPipe pipeline started · Biomechanics script in progress
- **Thursday merge:** All scaffolds committed · JSON contracts agreed · DB schema defined · Stub endpoints deployed

### Week 6 — Thin E2E Slice + Data Prep
**Theme:** First time all three squads connect. Real video → MediaPipe → biomechanics JSON → SSE → Results screen.

- **Squad 1:** Upload screen (with demo user selector dropdown) · Results screen (dummy → real data by end of week) · SSE client · Dashboard shell
- **Squad 2:** Real /upload endpoint (GCS + DB + analysis_id) · SSE orchestration · Nemotron A/B/C tests · Integrate Squad 3 biomechanics
- **Squad 3:** MediaPipe + quality gate + OpenCV overlay → `overlay_video_url` · Biomechanics script (angles, tempo, stability, bottom_frame per rep) · PT-02 gold standard data prep · MD file curation (5–10 coaching docs)
- **Thursday merge:** Real video → GCS → MediaPipe → biomechanics JSON → SSE fires → Results screen shows real data

### Week 7 — Full Pipeline
**Theme:** Full pipeline live — ~~Nemotron~~ → **Haiku 4.5** + MD coaching docs (system prompt) + ~~Claude Sonnet~~ → **Claude Haiku 4.5 — Call 2** *(W6 A/B test)* coaching. Worst-rep annotated frame on Results screen.

- **Thursday test:** Upload → get real coaching output with weight-specific advice → worst-rep annotated frame on Results screen

### Week 8 — Differentiation + Lifecycle
**Theme:** Progression recommendation live. Dashboard seeded. Workout Builder + Tracker. Profile shell.

- **Thursday test:** Does progression recommendation fire correctly using weight history from DB?

### Week 9 — Validation
**Theme:** Gold standard videos validated against PT experts. Latency confirmed under 35s. Dashboard seeded with compelling demo-day progression story for all 3 demo users.

- **Thursday test:** Do PT reviewers agree with coaching + recommendation outputs? Is the live demo smooth at 35s?

### Week 10 — UAT + Launch Criteria
**Theme:** Zero high-severity bugs · All demo-day launch criteria green · Demo accounts seeded with rich progression comparison data.

- **E2E flow:** Select demo user → upload → results → comparison → recommendation → dashboard progression story

---

## Scope Decisions

### New in v2 — Post mentor review

**Auth dropped — hardcoded user IDs for demo**
2–3 user IDs seeded in DB (`user_001`, `user_002`, `user_003`). Frontend Upload screen has a dropdown to select demo user. No JWT, no login screen, no session management. Enables switching between users to show different progression stories on dashboard.

**Vector DB dropped — MD files in Claude system prompt**
5–10 curated coaching documents (PT language, form cues, Goblet Squat references) converted to MD files and injected directly into ~~Claude Sonnet~~ → **Claude Haiku 4.5 — Call 2** *(W6 A/B test)*'s system prompt. No retrieval endpoint, no embeddings, no ingestion pipeline. Saves Squad 3's full RAG pipeline build.

**Profile screen — frontend shell only**
No backend profile endpoints. Screen exists, looks complete, displays dummy data. Auth onboarding removed — personalisation wired to AI coaching is post-demo.

**Gold standard added**
3–5 good-form reference videos run through pipeline → `gold_standard_biomechanics` DB table. Used by OpenCV Part 2 (angle overlay) and Claude system prompt (coaching reference values).

### Carried from v1

**Goblet Squat only for MVP**
One exercise enables deep, accurate biomechanics tuning. Generalising to multiple exercises is a post-demo milestone.

**~~Nemotron~~ → **Haiku 4.5** over GPT-4V for video analysis**
~~NVIDIA ~~Nemotron 3 Nano Omni~~ → **Claude Haiku 4.5 — Call 1** *(W6 A/B test)*~~ → **Claude Haiku 4.5 — Call 1** *(W6 A/B test)* confirmed as the video model. Per-rep scoring with chain-of-thought reasoning. Test C (overlay video + biomechanics JSON input) confirmed as the optimal input combination.

**OpenCV overlay video → ~~Nemotron~~ → **Haiku 4.5** input**
The full video with green skeleton lines drawn on every frame is what ~~Nemotron~~ → **Haiku 4.5** receives — confirmed more accurate than raw video. This overlay is NOT shown to the user; it is the AI input only.

**OpenCV Part 2 — worst-rep frame extraction (Option 3)**
Extract a single frame at the bottom position of the worst rep. Draw skeleton lines + joint markers (colour-coded) + actual angle text + gold standard reference range. The annotated frame is what the user sees on the Results screen.
