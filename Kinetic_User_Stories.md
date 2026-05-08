# Kinetic — User Stories
**Author:** Amrita
**Date:** May 7, 2026
**Last Updated:** May 8, 2026
**Status:** Draft v1.1

---

## Epic Structure

Stories are organised under the 6 outcome-oriented epics. Each epic answers one question a user needs answered.

| Epic | Outcome | Stories | Week |
|------|---------|---------|------|
| E1 — Identity & Access | I can log in and my sessions persist | US-01, US-03 | W7 |
| E2 — The Analysis Core | I upload a video and get actionable coaching | US-04, US-04b, US-05, US-06a, US-06b, US-07 | W6→W7 |
| E3 — Longitudinal Intelligence | I can see if I'm improving — and whether I'm ready to go heavier | US-08, PT-01 | W8 |
| E4 — Habit & Engagement Loop | I come back because I can see my progress | US-09, US-10 | W7–W8 |
| E5 — Workout Lifecycle | I plan and log my workout in one place | US-11a, US-11b | W8 |
| E6 — Personalization | Kinetic knows my body (frontend only in MVP) | US-02, US-12a, US-12b | W8–W9 |

---

## E1 — Identity & Access

**US-01 — Sign In**
> As a new user, I want to sign in with my Google account, so that I can get started without creating a new password.

**Acceptance Criteria:**
- Given I'm on the sign-in screen, when I tap "Continue with Google", then I'm authenticated via Google OAuth and my account is created automatically on first sign-in
- Given I've signed in before, when I tap "Continue with Google", then I'm logged into my existing account
- Given I'm logged in, when I navigate away and return within the session, then I'm not asked to sign in again

---

**US-03 — Returning User Login**
> As a returning user, I want to be taken directly to my Dashboard after signing in, so that I can pick up where I left off.

**Acceptance Criteria:**
- Given I'm a returning user, when I sign in with Google, then I'm taken to the Home screen — not onboarding
- Given I've signed in before, onboarding does not repeat — it is one-time only

---

## E2 — The Analysis Core

**US-04 — Filming Tips**
> As a user who doesn't know how to film themselves properly, I want in-app guidance on how to set up my camera, so that my video produces accurate analysis results.

**MVP scope:** Lightweight inline component only — Google image or short video showing the correct camera angle for Goblet Squat + 3–4 camera tips (distance, height, angle). No custom filming required. No separate modal screen.

**Acceptance Criteria:**
- Given I'm on the Upload screen, then I see filming tips inline — a Google image/video and 3–4 camera angle tips
- Given I'm on mobile web, then the tips are readable without zooming
- Given I dismiss or ignore the tips, then all my upload inputs (exercise, weight, video) remain intact

---

**US-04b — Video Submission** *(new)*
> As a user ready to analyse my form, I want to select my exercise, enter my weight, and upload a video, so that Kinetic can analyse my session.

**Acceptance Criteria:**
- Given I'm on the Upload screen, I can select an exercise (Goblet Squat for MVP)
- Given I've selected an exercise, I can enter the weight I used
- Given I tap to upload, my device's native file picker opens (photo library + files on mobile)
- Given I select a video, I see the filename confirmed so I know the right file was chosen
- Given the file is an unsupported format or too large, I see a clear inline error with guidance on what's accepted
- Given all fields are complete, the Submit button becomes active
- Given I tap Submit, I'm taken to the processing screen

---

**US-05 — Analysis Processing**
> As a user who just submitted a video, I want to see a clear processing status while Kinetic analyses my footage, so that I know it's working and roughly how long to wait.

**Acceptance Criteria:**
- Given I've submitted a video, when processing begins, then I see a progress indicator with stage labels (e.g. "Reading your movement patterns…", "Analysing your form…") — not a blank screen
- Given processing completes, then I'm automatically taken to the Results screen
- Given processing fails, then I see a clear error message with the option to retry

---

**US-06a — Analysis Results: Form Score, 4 Parameters & Rep Progression** *(split from US-06)*
> As a gym-goer training alone, I want to see my overall form score, a breakdown across 4 key parameters with coaching, a verdict, and my rep-by-rep progression, so that I immediately understand how I performed and what to prioritise next.

**Note:** W6 — Results screen built against Nemotron output schema using dummy data. Real output wires in W7 (or end of W6 if stretched goal hit).

**Acceptance Criteria:**

*Overall Form Score*
- Given analysis is complete, I see a consolidated form score /100 prominently at the top of the Results screen

*4 Parameter Breakdown (Posture · Stability · Movement Quality · Tempo)*
- Given the Results screen, I see 4 parameter sections — each showing:
  - Score /100 aggregated across all reps
  - 1 affirmation — what I did well in this parameter
  - 1 critical observation — the main issue identified
  - 1–2 actionable coaching tips — what to do differently next time
- Parameters are scannable — headline score and affirmation visible first, detail below

*Consolidated Verdict*
- Given the Results screen, I see a verdict section with 2–3 bullet points summarising my overall performance across the full set
- The verdict is distinct from the parameter detail — a quick-read summary for users who won't scroll

*Rep-by-Rep Progression*
- Given the Results screen, I see a chart showing my score per rep across the set
- The chart shows whether performance improved, held steady, or degraded across reps

*General*
- Given the full Results screen, all content is scannable in under 10 seconds — score and verdict first, parameter detail below
- Given I'm on mobile web, all sections are readable without zooming

---

**US-06b — Visual Joint Angle Overlay** *(split from US-06)*
> As a user viewing my results, I want to see an extracted frame from my video with joint angles highlighted, so that I can see visually exactly where my form broke down.

**Dependency:** Squad 2 must agree frame coordinate JSON schema with Squad 1 before build begins (W5/W6 contract).

**Acceptance Criteria:**
- Given analysis is complete, I see at least one extracted frame from my video on the Results screen
- Given the frame, correct joint angles are highlighted in green and deviations in red
- Given the frame, each flagged joint is labelled (e.g. "Knee: 142° — target <130°") so I understand the specific deviation
- Given I'm on mobile web, then the frame is full-width and labels are legible without zooming

---

**US-07 — Joint Corrections & Coaching Tips**
> As a user with a joint pain concern, I want to see exactly which joint angle is causing the issue, so that I know what to fix — not just that something is wrong.

**Acceptance Criteria:**
- Given my analysis is complete, when I view Results, then I see a minimum of 2 specific joint-level corrections (e.g. "Knee caves inward at bottom of rep")
- Given each correction, then I also see at least 1 actionable coaching tip explaining how to fix it
- Given the results are detailed, then they are scannable in under 10 seconds — score and recommendation first, details below

---

## E3 — Longitudinal Intelligence

**US-08 — Form Comparison & Progression Recommendation**
> As a user who has logged multiple sessions, I want to compare my current form analysis against my last session, so that I can see whether I'm improving or regressing.

**Acceptance Criteria:**
- Given I'm on the Results screen, then I see a **"Form Comparison" toggle**
- Given I tap the toggle, when I have a previous session for the same exercise within the last 2 months, then I see a **side-by-side view** showing:
  - Session date and weight logged for each
  - Overall form score for each
  - Detailed form scores (joint-level breakdown) for each
  - Joint angle overlay for each
  - Rep-by-rep score trend chart for each session side by side
- Given I tap the toggle, when I have **no previous session** for that exercise, then I see: *"Log more form analyses to see your performance progression"*
- Given I tap the toggle, when my **last session is older than 2 months**, then I see the same message
- Given the side-by-side view is active on mobile web, then the two panels are horizontally scrollable or stacked cleanly

---

**PT-01 — Progression Recommendation Logic Definition** *(product task)*

> PM + Physical Trainer define the exact ruleset that determines "Ready to progress" / "Hold at current weight" / "Drop weight" — before Squad 2 builds the logic in Week 8.

**Owner:** PM + Physical Trainer Expert 1
**Blocks:** S2-W8-01 (progression recommendation endpoint)

| Phase | Owner | Due | Deliverable |
|-------|-------|-----|-------------|
| Phase 1 — Biomechanics parameters + Nemotron output schema | PM | W5 (urgent) | Parameter definition doc + output schema agreed with Squad 1 |
| Phase 2 — Refine against real pipeline output | PM + Squad 2 | W7 | Revised thresholds based on real data |
| Phase 3 — Progression threshold spec | PM + PT Expert 1 | Mon W8 | Final spec handed to Squad 2 |
| Phase 4 — Expert validation | PT Experts 1 + 2 | W9 | Outputs reviewed on 3–5 test videos |

---

## E4 — Habit & Engagement Loop

**US-09 — Dashboard (Home Screen)**
> As a user, I want my home screen to show me a snapshot of my progress and prompt my next action, so that I can stay on top of my training habit.

**Acceptance Criteria:**
- Given I land on the Home screen, then I see three CTAs in order of priority:
  1. **"Upload Form Analysis"** — most prominent
  2. **"Build Your Workout Plan"**
  3. **"Start / Continue Workout"**
- Given I'm a **returning user with sessions**, then I see: last session summary (exercise name, date, weight, overall form score), form score trend chart, habit tracker
- Given I'm a **new user with no sessions**, then I see a motivational prompt encouraging them to upload their first form analysis
- Given I'm a **returning user whose last session is older than 2 months**, then I see last session data with a nudge to get back on track
- Given I'm on mobile web, then all three CTAs are thumb-reachable and the progress snapshot is scannable without scrolling

---

**US-10 — Session History**
> As a user reviewing my progress, I want to see a chronological list of my past sessions, so that I can revisit specific sessions and track how I've progressed.

**Acceptance Criteria:**
- Given I'm in the History tab, then I see all past sessions from the **last 6 months** in reverse-chronological order, each showing: exercise name, date, weight logged, overall form score
- Given I tap a past session, then I see the full Results screen for that session
- Given I have no sessions in the last 6 months, then I see an empty state with a prompt to upload
- Given sessions older than 6 months exist, then they are not shown in History

> **Open question:** Should sessions older than 6 months be permanently deleted or just hidden? Impacts data retention policy and privacy compliance — needs resolution before launch.

---

## E5 — Workout Lifecycle

**US-11a — Workout Builder**
> As a user planning my workout, I want to quickly build a workout plan by selecting muscle groups and exercises, so that I know what I'm doing before I start training.

**Acceptance Criteria:**
- Given I'm in the Workout Builder, then I see a list of broad muscle groups (e.g. Legs, Upper Body, Core)
- Given I select a muscle group, then I see a pre-built list of exercises for that group to choose from
- Given I see an exercise name, then I can tap it to open an **exercise detail overlay** showing: key form tips, image of primary muscles activated, embedded YouTube video of correct form
- Given I dismiss the overlay, then I return to the exercise list with my plan intact
- Given I select an exercise to add, then it is added to my workout plan for today
- Given an exercise is added, then I can specify the target number of sets for that exercise
- Given my plan is building, then I can add more exercises from the same or different muscle groups at any time
- Given my workout plan is ready, then I see a summary of all exercises and their target sets before I start

> **Hard dependency — Squad 3:** YouTube form videos and muscle activation images must be sourced and mapped per exercise by Thursday W7. If not ready, the exercise detail overlay is blocked. Fallback: exercise name + key form tips only, no media.

---

**US-11b — Workout Tracker**
> As a user mid-workout, I want to track my actual reps and weight per set as I go, so that my real performance is logged against my plan.

**Acceptance Criteria:**
- Given I'm on the Workout Tracker, then I see a **"Start Workout"** CTA to begin my session
- Given I start my workout, then I see each exercise from my plan with sets listed underneath
- Given I complete a set, then I can input my actual reps and weight and tap **"Save"** to confirm it is logged
- Given I want to add another set beyond my plan, then I can tap **"Add Set"** inline without leaving the screen
- Given I'm mid-workout, then I can add a new exercise (opens Workout Builder flow) and it is appended to my current session
- Given I've completed all sets, then my workout is saved and linked to my session history
- Given I uploaded a form analysis in the same session, then the workout log and form analysis are linked in History

---

## E6 — Personalization

**US-02 — Injury & Pain Onboarding**
> As a new user, I want to tell Kinetic about any injuries or pain I've experienced, so that my profile reflects my situation.

**MVP scope:** Injury data is collected and stored in the DB. It is **NOT** passed to the Claude Sonnet prompt in this version. Shown in the demo as a design decision — coaching personalisation based on injury history is a post-MVP feature.

**Acceptance Criteria:**
- Given I've just signed in for the first time, when onboarding begins, then I'm asked to select any areas of concern from a visual body map or joint/muscle list (e.g. knee, lower back, shoulder, hip)
- Given I've selected an area, when I proceed, then I'm asked to classify the issue: one-off pain (resolved) / recurring issue / past surgery or medical procedure
- Given I've selected a classification, when I proceed, then I see a free-text field to add any details (optional, clearly labelled as optional)
- Given I have no injuries, then I can select "No issues" and skip to the next step
- Given I complete the injury screen (or skip it), then my selections are saved to my Profile and I am routed to the Home screen

---

**US-12a — Training Preferences**
> As a user, I want to update my training preferences in my Profile, so that Kinetic's experience stays relevant as my training evolves.

**Acceptance Criteria:**
- Given I'm in Profile → Preferences, when I update my training frequency or exercise preferences, then changes are saved and reflected in my next session

---

**US-12b — Injury & Pain Profile**
> As a user, I want to update my injury and pain profile in Preferences at any time, so that Kinetic's coaching stays accurate if my situation changes.

**Acceptance Criteria:**
- Given I'm in Profile → Preferences, when I open "Injury & Pain", then I see my saved selections (areas, classification, free text) and can edit them
- Given I update my injury profile, then changes are saved and applied to all future analysis sessions
- Given I previously skipped the injury onboarding, then the Injury & Pain section in Preferences shows as empty and editable

---

## Out of Scope (Not in MVP)
- Real-time camera analysis
- In-browser video recording ("Record" option — stretched goal only)
- Mobile native app
- Shoulder Press (stretched goal — only if Goblet Squat hits ≥80% accuracy by Week 9)
- B2B creator portal
- Injury-personalised AI coaching (US-02 data collected and stored, not passed to LLM in MVP)

---

## Cross-Squad Dependencies

| Story | Dependency | Squads | Due |
|-------|-----------|--------|-----|
| US-04b | Frame coordinate JSON schema agreed for video submission POST shape | S1 + S2 | Thu W5 |
| US-06b | Frame coordinate JSON schema for overlay rendering (joint coordinates, angle values, pass/fail) | S1 + S2 | Thu W6 |
| US-08 | Past session data retrieval endpoint for comparison view | S1 + S2 | Thu W8 |
| US-11a | YouTube form videos + muscle activation images per exercise sourced and mapped | S1 + S3 | Thu W7 |
| PT-01 | Final progression logic spec handed to Squad 2 before W8 build begins | PM → S2 | Mon W8 |

---

**Changelog:**
- May 7, 2026: Initial draft — created through collaborative sparring session with PM
- May 8, 2026: Restructured to E1–E6 epic format · US-03 ACs cleaned (removed misplaced file picker ACs, moved to US-04b) · US-04 updated (lightweight inline component, no custom filming, no separate modal) · US-04b added (Video Submission — was missing from original) · US-06 split into US-06a (Basic Results, W6) and US-06b (Visual Overlay, W7) · US-02 updated (frontend only — data stored, NOT passed to LLM in MVP; removed AI pipeline AC) · PT-01 added (Product Task — Progression Logic Definition, 4-phase delivery W5–W9) · Cross-squad dependencies updated · Out of scope updated
