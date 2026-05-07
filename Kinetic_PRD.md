# Lean Startup PRD
## (Linear, Figma, Y Combinator Style)

**Best for:** Startups, MVPs, fast-moving teams  
**Length:** 2-4 pages  
**Philosophy:** Ship fast, iterate based on data

---

## Product Name: Kinetic

**Author:** [Your Name]  
**Date:** May 4, 2026  
**Status:** Draft  
**Last Updated:** May 4, 2026

---

## TL;DR (Executive Summary)

**One-sentence pitch:**
Kinetic is the first AI form coach that tracks you across weights — not just one rep, but your entire journey. It spots where your form breaks down as load increases, then tells you exactly how to fix it, because it knows your history.

**Problem:**
Intermediate gym-goers training alone in small gyms have no reliable feedback loop on their form. They get injured, plateau, or develop bad habits for weeks before anyone tells them — because there's nobody watching.

**Solution:**
Upload a workout video with your weight. Kinetic uses computer vision and AI grounded in exercise science to score your form, identify joint-angle breakdowns, and tell you whether you're ready to progress — across your entire training history.

**Success Metrics:**
- Weekly returning users (habit formation)
- Form analysis uploads per user per month (engagement depth)

---

## Context & Background

### Why Now?

**User pain point:**
Intermediate gym-goers (3+ months training, 1–2x strength sessions per week) working out in small, home, or building gyms have no trainer, no spotter, and no reliable feedback on whether their form is safe or progressing. The result:

1. **Fear-driven plateaus:** A pain signal (e.g. knee pain on Goblet Squat) causes them to stay at the same weight for months, unsure if it's safe to progress
2. **Blind form drift:** Bad form goes undetected for weeks or months until a stranger at the gym happens to mention it
3. **Lagging soreness signals:** Unusual next-day soreness at unexpected muscles/joints signals something was wrong — but the moment is already gone
4. **Invisible stagnation:** Feeling "too comfortable" with no way to know if they're actually progressing or just going through the motions

**Current workarounds:**
- Watch YouTube tutorials (generic, not personalised to their form)
- Self-record and watch back, or check in the mirror (raw footage, no interpretation)

**Evidence:**
- [Insert VOC interview quotes — target 3–5 direct user quotes from research]
- [Insert quantitative survey results from Weeks 3–4 research]

**Competitive gap:**
Apps like Gymscore, Zing, and FormAI provide snapshot form feedback — they detect symptoms in a single video. None of them track form *across weights over time* or integrate workout logging. Kinetic is the first to connect form quality to progressive overload history.

**What happens if we don't build this:**
Users continue guessing. They plateau, get hurt, or quit. The pain points are real and recurring, and the existing tools leave a significant gap — particularly for the underserved intermediate lifter training without supervision.

---

## Goals & Success Metrics

### Primary Goal
Validate that users find longitudinal AI form coaching valuable enough to build a weekly habit around it — returning, uploading videos, and progressing their weights with Kinetic's guidance.

### Success Metrics

**North Star Metric:**
- Metric: Weekly Active Users who complete at least 1 form analysis session
- Current: 0 (pre-launch)
- Target: 50 WAU within 4 weeks of public launch
- Timeline: By end of June 2026

**Supporting Metrics:**

1. **Form Analysis Uploads per User per Month:** Target ≥4 uploads/user/month (consistent weekly usage)
2. **Form Analysis Accuracy:** ≥80% expert agreement rate on AI form scores (validated on 20–30 test videos, Week 9)
3. **Weight Progression Rate:** % of users who increase their logged weight within 30 days of receiving a "ready to progress" recommendation
4. **Trial-to-Paid Conversion:** Target ≥15% of trial users convert to $15/month subscription

### Anti-Metrics (What we DON'T want to move)
- User-reported pain or injury following a "safe to progress" recommendation (zero tolerance)
- Session time inflated by confusing UX — value must be delivered fast and clearly
- Churn driven by form advice users can't act on (vague or overly technical output)

---

## Target Users

### Primary Persona: "The Unsupervised Intermediate"

**Demographics:**
- Age: 18–35
- Training experience: 3+ months, intermediate level
- Workout frequency: 1–2x strength training sessions per week minimum
- Gym type: Home gym, building gym, school gym — small, low-supervision environments
- Equipment: Free weights (dumbbells, barbells), compound movements

**Behaviors:**
- Currently uses: YouTube for form tutorials; records themselves or checks the mirror after sets
- Pain point: No personalised feedback loop — form doubts linger for weeks, weights stall due to fear, and bad habits go uncorrected
- Frequency: Form uncertainty arises every training session, especially as weight increases

**Quote:**
> "[Insert direct user quote from VOC research — e.g. 'I've been stuck at the same weight for 3 months because my knee starts hurting and I don't know if I'm doing something wrong']"

### Secondary Personas
- **Online Fitness Coaches / Content Creators** (future B2B): Want to offer form tracking as a value-add to their audience without building the tech themselves
- **Injury-returning gym-goers**: Cautious about reloading weight after injury; need objective form validation before progressing

---

## Proposed Solution

### High-Level Overview
Kinetic is a web app where users log their workouts (exercise, sets, reps, weight) and upload exercise videos. The backend runs MediaPipe to extract joint angles and biomechanical parameters, then queries a RAG pipeline grounded in exercise science to generate structured coaching feedback. Critically, every analysis is contextualised against the user's full history — Kinetic knows what your Goblet Squat looked like at 10kg, 15kg, and 20kg, and can tell you exactly where your form degraded and why.

### User Flow

```
1. User logs in → selects exercise (e.g. Goblet Squat) + enters weight
   ↓
2. Uploads workout video from session
   ↓
3. Kinetic processes video:
   MediaPipe extracts joint keypoints & angles per rep
   RAG retrieves relevant biomechanics context
   Nemotron 3 Nano Omni generates structured JSON + chain-of-thought
   Claude Sonnet produces coaching output
   ↓
4. User sees results:
   → Form score (overall)
   → Joint-angle corrections (specific: "knee caves inward at bottom of rep")
   → Weight-based recommendation ("Your form at 12kg is solid. You're ready for 14kg.")
   → Comparison to past sessions ("Form has improved since 10kg. Hip hinge degraded at 14kg+.")
   ↓
5. Session saved to history
   ↓
6. Dashboard shows form score trends across weights and time
```

### Key Features (MVP Scope)

**Must-Have (P0):**

1. **Video Upload & Processing Pipeline (Goblet Squat)**
   - What: User uploads a video; backend runs MediaPipe pose detection and extracts rep-level biomechanical parameters (joint angles, stability, posture, rep count, rep time)
   - Why: Core engine — without this, nothing else works
   - Acceptance criteria: Video processed end-to-end in <30 seconds; keypoints extracted accurately across rep range; works on consumer-filmed video with provided filming guidelines

2. **AI Form Analysis Output**
   - What: RAG-enhanced Gemini generates a structured report: form score, joint-angle corrections, Movement Quality / Stability / Posture ratings, rep count, rep time, and specific coaching tips
   - Why: The primary user value — actionable, science-backed feedback personalised to their video
   - Acceptance criteria: Output includes overall score, minimum 2 specific joint corrections, and at least 1 actionable coaching tip; ≥80% expert agreement in validation testing (Week 9)

3. **Weight-Based Progression Recommendation**
   - What: Kinetic compares current session form against past sessions at lower weights and outputs a clear recommendation: "Ready to progress" / "Hold at current weight" / "Drop weight and fix X first"
   - Why: This is the core differentiator — not just "what's wrong" but "are you ready to go heavier"
   - Acceptance criteria: Recommendation generated when ≥2 sessions logged for the same exercise; recommendation logic validated against expert assessment

4. **Workout Logging (Builder & Tracker)**
   - What: Users log workouts — exercise, sets, reps, weight — linked to form analysis sessions
   - Why: Creates the longitudinal data layer that powers progression recommendations; eliminates app-switching during workouts
   - Acceptance criteria: User can create, save, and retrieve workout logs; logs linked to form sessions in history

5. **Session History & Dashboard**
   - What: Chronological view of all form sessions with score trends, weight progression, and side-by-side comparisons across sessions
   - Why: Builds the habit loop — users need to see their journey to stay engaged
   - Acceptance criteria: Dashboard displays form score trend by exercise across weights and time; filterable by exercise

6. **User Authentication & Profile**
   - What: Sign-up/login, basic profile (exercise preferences, training frequency)
   - Why: Required to persist and personalise longitudinal data
   - Acceptance criteria: User can sign up, log in, and all sessions persist to their account

**Stretched Goals — MVP (If Time Permits):**

1. **"Record" option on the video capture screen**
   - What: Alongside the existing "Upload from file" option, users can record directly in-browser using their device camera
   - Why: Reduces friction for users who want to film and analyse in a single step; no export/transfer required
   - Condition: Only if upload pipeline is stable and latency targets are met by Week 9; must not delay core P0 delivery
   - Owner: Squad 1 (frontend only — backend pipeline is identical)

2. **Shoulder Press as 2nd exercise**
   - What: Extend the MediaPipe + RAG + analysis pipeline to support Shoulder Press with its own biomechanics corpus, joint parameters (shoulder, elbow, torso), and ideal angle ranges
   - Why: Validates that the pipeline generalises beyond a single exercise and broadens user value before launch
   - Condition: Only after Goblet Squat hits ≥80% accuracy threshold (Week 9); Shoulder Press data sourcing and parameter definition must be complete
   - Owner: Squad 2 (pipeline extension) + Squad 3 (corpus + RAG for Shoulder Press)

3. **Design enhancements**
   - What: Visual polish beyond functional MVP — motion transitions between SSE processing states, score visualisation animations, improved data visualisation on the Dashboard (chart styling, trend callouts), micro-interactions on key actions (upload complete, recommendation revealed)
   - Why: Elevates the product feel for the final pitch demo and first user cohort; strong first impression drives word-of-mouth
   - Condition: Only after all P0 screens are approved and UAT-ready; design team leads this in Week 9 polish pass
   - Owner: Squad 1 (Design + FE)

**Post-MVP (P2 — Future):**
- Full compound lift library (Deadlift, Bench Press, OHP, Romanian Deadlift)
- Creator/coach portal: coaches embed their workout plans into Kinetic for their audience
- Mobile native app (web-first for MVP)
- Real-time live camera analysis
- Side-by-side visual comparison: user's video frame vs. ideal form reference
- Image extraction from user video with overlaid joint angles and corrective arrows

---

## Out of Scope

**What we're NOT building (and why):**
1. **Multiple exercises beyond Goblet Squat** — Reason: Accuracy must be validated deeply on 1 exercise first; Shoulder Press is a stretched goal only if Goblet Squat hits ≥80% accuracy by Week 9
2. **Real-time live camera analysis** — Reason: Pipeline latency (MediaPipe + Nemotron + Claude Sonnet) makes real-time infeasible; "Record" in-browser is a stretched goal but still uses the same async pipeline
3. **Mobile native app** — Reason: Web-first (responsive) for POC; mobile post-validation
4. **Nutrition or general fitness tracking** — Reason: Outside core value prop; competitive and crowded space
5. **B2B creator portal** — Reason: Phase 2 initiative; requires validated B2C user base first

---

## Design & User Experience

### Key Screens/States
1. **Onboarding / Sign-up** — Account creation, exercise preferences, training frequency
2. **Video Upload** — Exercise selection, weight entry, upload interface, filming tips overlay
3. **Analysis Results** — Form score, joint corrections, weight-based recommendation, rep metrics
4. **Dashboard (Home)** — Progress trends, last session summary, streak/habit tracker
5. **History** — Session list with form score trends across weights
6. **Workout Planner / Tracker** — Log sets, reps, weight; link to form sessions
7. **Profile** — Settings, training preferences

### Design Requirements
- Results must be scannable in <10 seconds — score and recommendation first, detail below
- Weight-based recommendation must be visually prominent (this is the key output)
- Mobile-responsive even as a web app — users will view results on their phone in the gym
- Clean, performance-focused aesthetic (not clinical); motivating, not intimidating
- Filming tips screen must be accessible before upload — this affects analysis quality

**Design References:**
- [Figma design system — Week 4/5 deliverable]
- [Prototype screens for devs — Week 8 deliverable]

---

## Technical Considerations

### Technical Approach
- **MVP Delivery:** Responsive web application (React + Tailwind) — web-first to validate the full pipeline end-to-end as a POC before native mobile investment
- **Pose Detection:** MediaPipe (Python) extracts joint keypoints per rep, computes structured biomechanics output: joint angles (knee, hip, torso), stability, posture, rep count, rep time
- **Video Analysis Model:** NVIDIA Nemotron 3 Nano Omni receives **both** the raw video and MediaPipe's structured biomechanics output as dual inputs — the model cross-references visual context against computed joint data to generate accurate, grounded form analysis
- **RAG Pipeline:** Biomechanics corpus (research papers, YouTube transcripts, exercise tutorials, muscle anatomy images) indexed for retrieval; Nemotron 3 Nano Omni generates coaching output grounded in this corpus
- **Progression Logic:** Weight-tagged session history queried to contextualise current form against past sessions at same/lower weights
- **Backend:** Python API on GCP, API Gateway
- **Frontend:** React + Tailwind (responsive web app), hosted on Vercel — auto-deploy on push to dev, per-branch preview URLs
- **Storage:** GCP / S3 for video files; database for exercise logs, form scores, angles, rep data, user history

### Dependencies
- **Backend:** MediaPipe Python library, Nemotron 3 Nano Omni (NVIDIA), GCP (Cloud Storage, API Gateway)
- **Frontend hosting:** Vercel (confirmed W5)
- **Frontend:** React, Tailwind
- **Data:** 20–30 curated sources per exercise (research papers, YouTube, Kaggle, Instagram tutorials, biomechanics references) for RAG corpus

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Video upload + progress stream architecture** | Option A for demo day → Option B before beta | Option A: single POST endpoint handles upload + streams SSE progress back on same connection. Simpler, sufficient for demo day in a controlled WiFi environment. Option B: upload returns `analysis_id`, frontend opens a separate SSE connection for progress — adds reconnection support essential for real users on mobile/gym networks. Option B scoped as first infrastructure task before beta rollout. |

---

### Technical Risks

1. **MediaPipe accuracy on consumer-filmed video** — Camera angle, lighting, clothing all affect keypoint extraction quality
   - Mitigation: Define filming guidelines (Week 4); validate on 20–30 diverse sample videos; provide in-app tips before upload

2. **Model hallucination on form advice** — Incorrect advice could cause injury (highest-severity risk)
   - Mitigation: Dual-input to Nemotron 3 Nano Omni (raw video + MediaPipe biomechanics) reduces reliance on visual interpretation alone; all outputs grounded in RAG corpus; expert validation pass before launch; confidence threshold to flag low-certainty outputs rather than fabricate

3. **End-to-end latency >30s** — Video processing + RAG + LLM generation chain may degrade UX
   - Mitigation: Async processing with clear progress indicator; dedicated optimisation sprint Week 9

4. **Progression recommendation logic accuracy** — Insufficient history data or wrong thresholds could recommend unsafe weight increases
   - Mitigation: Require minimum 2 sessions before surfacing recommendations; expert review of recommendation logic; conservative initial thresholds

**Engineering POC:** [Name — TBD]

---

## Timeline & Milestones

| Phase | Deliverable | Owner | Date |
|-------|------------|-------|------|
| Weeks 1–2 | Product idea, Designer pitch | Product / Design | Apr 6–13 |
| Weeks 3–4 | VOC research (qual + quant), Developer pitch, Design mockups, Tech requirements | All | Apr 20–27 |
| Weeks 4–5 | Data sourcing for RAG (20–30 sources, Goblet Squat), Blueprint (user flow/screens), Design system finalised | Design + Data | Apr 27 – May 4 |
| Weeks 5–6 | Infra setup (GCP, React, Tailwind, API Gateway), MediaPipe exploration, Video pipeline + RAG setup, Gemini integration, Prompt engineering v1 | Engineering | May 4–17 |
| Week 7 | Enhanced RAG + DB setup, Form comparison prompt engineering, Exercise Builder + Tracker frontend, Form Comparison output, Sample videos defined (20–30) | Engineering + Design | May 18 |
| Week 8 | DB schema refinement, RAG audio/image sources added, Prompt engineering refined, Prototype screens for devs, Onboarding + workout planner screens | Engineering + Design | May 25 |
| Week 9 | Accuracy validation testing (20–30 videos), Prompt/RAG refinement, End-to-end latency optimisation | Engineering | Jun 1 |
| Week 10 | UAT + E2E testing, Final pitch preparation | All | Jun 8 |
| Week 11 | Final pitch / launch | All | Jun 15 |

**Target Launch Date:** June 15, 2026

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MediaPipe inaccurate on consumer-filmed video | High | High | Filming guidelines + diverse sample validation (Week 9) |
| LLM generates incorrect/harmful form advice | Med | High | RAG grounding + expert validation + confidence thresholds |
| Progression recommendation triggers unsafe weight increase | Low | High | Conservative thresholds + min 2-session gate + expert review |
| End-to-end latency >30s degrades UX | Med | Med | Async UX + pipeline optimisation sprint (Week 9) |
| Scope creep beyond 1 exercise before accuracy validated | High | Med | Hard scope lock: Goblet Squat only until ≥80% accuracy achieved |
| Insufficient RAG corpus quality for Goblet Squat | Med | High | Dedicated data sourcing milestone (Weeks 4–5), 20–30 source target |

---

## Launch Criteria

**Before we ship, we must have:**
- [ ] Goblet Squat analysis pipeline working end-to-end
- [ ] ≥80% expert agreement on form scoring accuracy (20–30 test videos)
- [ ] Weight-based progression recommendation validated by expert reviewer
- [ ] End-to-end latency <30 seconds
- [ ] All P0 features complete and functional
- [ ] Design prototype approved by team
- [ ] UAT passed (Week 10)
- [ ] Metrics instrumented (session uploads, form scores, recommendation events, retention)
- [ ] Filming guidelines published in-app
- [ ] Zero high-severity bugs in E2E test suite
- [ ] Privacy policy in place for video data storage

---

## Go-to-Market

### Launch Plan
- **Phase 1 (Launch):** Free 14–30 day trial with 2–3 form analysis uploads per week; convert to $15/month subscription
- **Announcement:** Demo day / final pitch June 15, 2026; VOC participants as first cohort (warm, pre-engaged users)
- **Rollout:** Closed beta → VOC participants first → open access
- **Support:** In-app filming guidelines; FAQ for common form questions

### Phase 2 (Post-Validation): B2B Creator Partnerships
- Partner with online fitness coaches and content creators who publish workout plans
- Integrate their plans into Kinetic; offer $10/month pricing for their audience
- Creator distribution removes CAC; Kinetic provides the tech layer they don't want to build

### Target Audience for Launch
- VOC interview participants: First 20–30 users (high intent, already engaged)
- Intermediate gym-goers in online communities (Reddit r/fitness, fitness Discord servers): Broader launch

---

## Appendix

### User Stories

1. As an intermediate gym-goer, I want to upload my Goblet Squat video with my weight, so I can get specific feedback on what I'm doing wrong and whether it's safe to increase weight
2. As a user stuck at the same weight due to knee pain, I want to know exactly which joint angle is causing the issue, so I can fix it confidently and progress
3. As a regular user, I want to see how my form score has changed across weights over time, so I can see that I'm actually improving — not just going through the motions
4. As a user who trains alone, I want a single app that logs my workouts and analyses my form, so I don't have to switch between tools during my session

### Open Questions

1. **Which specific joint parameters define a "good" Goblet Squat?** — Owner: [Research Lead] — Biomechanics research must define ideal angle ranges for knee, hip, and torso before accuracy can be validated
2. **What is the minimum number of sessions before a progression recommendation is surfaced?** — Owner: Engineering + Product — Too few sessions = unreliable; too many = frustrating delay
3. **Who are the human experts validating form scores?** — Owner: [Founder] — Certified PT, physiotherapist, or sports scientist? Must be confirmed before Week 9
4. **How are user videos stored and for how long?** — Owner: Engineering + Legal — Videos contain biometric data; retention policy and privacy compliance needed before launch
5. **What confidence threshold triggers a "low certainty" flag vs. full analysis output?** — Owner: Engineering — Needs calibration from validation testing
6. **Freemium limit: 2 or 3 uploads per week during trial?** — Owner: Product — Affects activation rate vs. conversion incentive trade-off

### References
- [VOC research results — Weeks 3–4]
- [Figma design system — Week 4/5]
- [RAG data sources index — Week 5]
- [Biomechanics research corpus (Goblet Squat) — Week 5]
- [Sample videos for testing (20–30) — Week 7]
- [MediaPipe documentation]
- [Nemotron 3 Nano Omni documentation (NVIDIA)]

---

**Changelog:**
- May 4, 2026: Initial draft — created from founder interviews and project roadmap
- May 4, 2026: Added stretched goals (Record option, Shoulder Press, Design enhancements); updated Out of Scope to reflect; fixed AI pipeline references (Nemotron + Claude Sonnet)

---
