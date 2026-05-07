# Kinetic — User Stories
**Author:** Amrita
**Date:** May 7, 2026
**Status:** Draft v1.0

---

## Epic 1: Account & Onboarding

**US-01 — Sign In**
> As a new user, I want to sign in with my Google account, so that I can get started without creating a new password.

**Acceptance Criteria:**
- Given I'm on the sign-in screen, when I tap "Continue with Google", then I'm authenticated via Google OAuth and my account is created automatically on first sign-in
- Given I've signed in before, when I tap "Continue with Google", then I'm logged into my existing account
- Given I'm logged in, when I navigate away and return within the session, then I'm not asked to sign in again

---

**US-02 — Injury & Pain Onboarding**
> As a new user, I want to tell Kinetic about any injuries or pain I've experienced, so that my form coaching stays conservative and appropriate for my body.

**Acceptance Criteria:**
- Given I've just signed in for the first time, when onboarding begins, then I'm asked to select any areas of concern from a visual body map or joint/muscle list (e.g. knee, lower back, shoulder, hip)
- Given I've selected an area, when I proceed, then I'm asked to classify the issue:
  - One-off pain (resolved)
  - Recurring issue
  - Past surgery or medical procedure
- Given I've selected a classification, when I proceed, then I see a free-text field to add any details (optional, clearly labelled as optional)
- Given I have no injuries, then I can select "No issues" and skip to the next step
- Given I complete the injury screen (or skip it), then my selections are saved to my Profile under Preferences and I am routed to the Home screen
- Given my injury data is saved, then the AI coaching pipeline receives this context and defaults to conservative recommendations for flagged joints

---

**US-03 — Returning User Login**
> As a returning user, I want to be taken directly to my Dashboard after signing in, so that I can pick up where I left off.

**Acceptance Criteria:**
- Given I'm a returning user, when I sign in with Google, then I'm taken to the Home screen — not onboarding (onboarding is one-time only)
- Given I tap "Upload" on mobile web, then the browser opens my device's native file picker (photo library + files)
- Given I select a video from my library, then it is attached to my session and ready to submit
- Given the selected file is an unsupported format or too large, then I see a clear inline error with guidance on what's accepted

---

## Epic 2: Video Upload

**US-04 — Filming Tips**
> As a user who doesn't know how to film themselves properly, I want in-app guidance on how to set up my camera before I record, so that my video produces accurate analysis results.

**Acceptance Criteria:**
- Given I'm on the Upload screen, then I see a **summary filming tips section** inline on the page (e.g. 2–3 quick tips: camera height, distance, angle)
- Given I want more detail, when I tap "Detailed Filming Tips", then an overlay opens with comprehensive guidance specific to Goblet Squat (camera position, lighting, clothing, background)
- Given the overlay is open, when I tap to dismiss it, then I return to the Upload screen with all my inputs (exercise, weight, video) intact
- Given I'm on mobile web, then the overlay is full-screen and readable without zooming

---

## Epic 3: Analysis Processing

**US-05 — Analysis Processing**
> As a user who just submitted a video, I want to see a clear processing status while Kinetic analyses my footage, so that I know it's working and roughly how long to wait.

**Acceptance Criteria:**
- Given I've submitted a video, when processing begins, then I see a progress indicator with stage labels (e.g. "Extracting joint data", "Generating feedback") — not a blank screen
- Given processing completes, then I'm automatically taken to the Results screen
- Given processing fails, then I see a clear error message with the option to retry

---

## Epic 4: Analysis Results

**US-06 — Form Score & Joint Angle Overlay**
> As a gym-goer training alone, I want to see my overall form score and a visual breakdown of my joint angles, so that I can immediately understand what was good and what broke down.

**Acceptance Criteria:**
- Given my analysis is complete, when I land on Results, then I see at least one extracted frame from my video with joint angle overlays displayed on it
- Given the overlay, then correct angles are highlighted in **green** and deviations are highlighted in **red**
- Given the overlay, then each flagged joint is labelled (e.g. "Knee: 142° — target <130°") so I understand the specific deviation
- Given I'm on mobile web, then the frame is full-width and labels are legible without zooming
- Given the Results screen, then I see my **overall form score + 1-line summary** below the visual
- Given the Results screen, then I see a **rep-by-rep score trend chart** showing how my form score changed from rep 1 to the last rep of the set

---

**US-07 — Joint Corrections & Coaching Tips**
> As a user with a joint pain concern, I want to see exactly which joint angle is causing the issue, so that I know what to fix — not just that something is wrong.

**Acceptance Criteria:**
- Given my analysis is complete, when I view Results, then I see a minimum of 2 specific joint-level corrections (e.g. "Knee caves inward at bottom of rep")
- Given each correction, then I also see at least 1 actionable coaching tip explaining how to fix it
- Given the results are detailed, then they are scannable in under 10 seconds — score and recommendation first, details below

---

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
- Given I tap the toggle, when my **last session is older than 2 months**, then I see the same message: *"Log more form analyses to see your performance progression"*
- Given the side-by-side view is active on mobile web, then the two panels are horizontally scrollable or stacked cleanly — not squeezed into an unreadable layout

---

## Epic 5: Dashboard & History

**US-09 — Dashboard (Home Screen)**
> As a user, I want my home screen to show me a snapshot of my progress and prompt my next action, so that I can stay on top of my training habit.

**Acceptance Criteria:**
- Given I land on the Home screen, then I see three CTAs in order of priority:
  1. **"Upload Form Analysis"** — most prominent
  2. **"Build Your Workout Plan"**
  3. **"Start / Continue Workout"**
- Given I'm a **returning user with sessions**, then I see:
  - Last session summary (exercise name, date, weight, overall form score)
  - Form score trend chart across recent sessions
  - Habit tracker (e.g. "3 sessions this month")
- Given I'm a **new user with no sessions**, then in place of the progress snapshot I see a motivational prompt encouraging them to upload their first form analysis (e.g. "Your form journey starts here — upload your first session")
- Given I'm a **returning user whose last session is older than 2 months**, then the progress snapshot shows their last session data with a nudge to get back on track (e.g. "It's been a while — ready to check your form?")
- Given I'm on mobile web, then all three CTAs are thumb-reachable and the progress snapshot is scannable without scrolling

---

**US-10 — Session History**
> As a user reviewing my progress, I want to see a chronological list of my past sessions, so that I can revisit specific sessions and track how I've progressed.

**Acceptance Criteria:**
- Given I'm in the History tab, when I scroll, then I see all past sessions from the **last 6 months** in reverse-chronological order, each showing:
  - Exercise name
  - Date
  - Weight logged
  - Overall form score
- Given I tap a past session, then I see the full Results screen for that session
- Given I have no sessions in the last 6 months, then I see an empty state with a prompt to upload their first form analysis
- Given sessions older than 6 months exist, then they are not shown in History

> **Open question:** Should sessions older than 6 months be permanently deleted or just hidden? Impacts data retention policy and privacy compliance — needs resolution before launch.

---

## Epic 6: Workout Planning & Tracking

**US-11a — Workout Builder**
> As a user planning my workout, I want to quickly build a workout plan by selecting muscle groups and exercises, so that I know what I'm doing before I start training.

**Acceptance Criteria:**
- Given I'm in the Workout Builder, then I see a list of broad muscle groups (e.g. Legs, Upper Body, Core)
- Given I select a muscle group, then I see a pre-built list of exercises for that group to choose from
- Given I see an exercise name, then I can tap it to open an **exercise detail overlay** showing:
  - Key form tips for that exercise
  - Image of primary muscles activated
  - Embedded YouTube video of correct form
- Given I dismiss the overlay, then I return to the exercise list with my plan intact
- Given I select an exercise to add, then it is added to my workout plan for today
- Given an exercise is added, then I can specify the target number of sets for that exercise
- Given my plan is building, then I can add more exercises from the same or different muscle groups at any time
- Given my workout plan is ready, then I see a summary of all exercises and their target sets before I start

> **Note for Squad 3 (Data):** YouTube videos and muscle activation images need to be sourced and mapped to each exercise in the pre-built list — scope alongside RAG corpus work.

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

## Epic 7: Profile & Settings

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

---

## Cross-Squad Dependencies
| Story | Dependency | Squads Involved |
|-------|-----------|-----------------|
| US-02 | Injury data must be stored in DB and passed to Claude Sonnet prompt | Squad 1 + Squad 2 |
| US-06 | Frame extraction (backend) + overlay rendering (frontend) — JSON schema for joint coordinates, angle values, pass/fail must be agreed upfront | Squad 1 + Squad 2 |
| US-08 | Past session data retrieval for comparison view | Squad 1 + Squad 2 |
| US-11a | YouTube video + muscle image sourcing per exercise | Squad 1 + Squad 3 |

---

**Changelog:**
- May 7, 2026: Initial draft — created through collaborative sparring session with PM
