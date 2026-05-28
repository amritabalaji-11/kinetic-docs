# Haiku Call 2 — What Needs to Happen

**Status:** Ready for Developer Review
**Created:** May 2026
**Reference prompt:** `LLM Prompt/Kinetic — Haiku Call 2 System & User Prompt v1.0.md`

---

## Demo Scope Note

**OpenCV Part 2 (automated annotated frame generation) is excluded from demo scope.**
Annotated frames for demo are handled manually — see Action 4 for the demo workaround.

---

## Context

When Haiku Call 1 finishes and the user is reading the Analysis tab, the Progression tab starts loading in the background. The user has not navigated to it yet.

The Progression tab has two data sources:
- **DB fields** (available immediately after Call 1)
- **Haiku Call 2 fields** (arrive async, a few seconds later)

---

## Progression Tab: What Data Lives Where

| Field | Source | Table |
|---|---|---|
| Current session: overall score, weight, date, 4 parameter scores | Call 1 output | `form_analysis_results` (current `analysis_id`) |
| Previous session: overall score, weight, date, 4 parameter scores | Call 1 output | `form_analysis_results` (most recent prior `analysis_id` by date) |
| "What we told you" text | `next_session_focus` from **previous session's** `analysis_id` | `form_analysis_results` |
| Current session annotated frame | `annotated_frame_url` | `user_profile` (demo workaround — live uploads won't have OpenCV automated) |
| Previous session annotated frame | `annotated_frame_url` | `form_analysis_results` (manually saved for demo past videos) |
| `progression_verdict`, `weight_recommendation` | Haiku Call 2 output | `haiku_call_2_outputs` |
| `posture_trend`, `stability_trend`, `range_of_motion_trend`, `movement_quality_trend` | Haiku Call 2 output | `haiku_call_2_outputs` |

---

## Action 1 — Start Haiku Call 2 async job

**What needs to happen:**
Immediately after Call 1 results are saved to the DB, kick off the Haiku Call 2 job in the background. The user should not wait for this — it runs while they read the Analysis tab.

**How to make it happen:**

| Option | Description | Effort |
|---|---|---|
| A — Fire-and-forget after Call 1 save | After writing Call 1 output to DB, immediately enqueue Call 2 as a background task | Low. Reuses existing async job pattern from the pipeline. **Recommended.** |
| B — Polling | Frontend polls for Call 2 completion on an interval | Higher frontend complexity, unnecessary since SSE is already live. Not recommended. |

---

## Action 2 — Check if prior session exists

**What needs to happen:**
Before assembling the Haiku Call 2 prompt, check whether the user has a prior session with form analysis in `form_analysis_results`. If not, skip the Haiku call entirely and emit the appropriate SSE event.

**How to make it happen:**
Query `form_analysis_results` for the most recent `analysis_id` for this user + exercise, excluding the current session. If no row is found:
- Do not call Haiku
- Emit SSE event: `haiku_call_2_no_history`
- Frontend receives this and shows: *"No past sessions yet — come back after your next workout to see your progression."*

If a prior session exists, continue to Action 3.

---

## Action 3 — Fetch previous session data

**What needs to happen:**
Pull the most recent prior session from `form_analysis_results` — ordered by date, excluding the current `analysis_id`. This row provides:
- Previous session: overall score, weight, date, 4 parameter scores
- Previous session annotated frame URL
- `next_session_focus` → used as the **"What we told you"** text in the Progression tab

**How to make it happen:**

```sql
SELECT
  id AS analysis_id,
  created_at,
  weight_value,
  weight_unit,
  haiku_call_1_output->>'overall_form_score' AS overall_score,
  haiku_call_1_output->'summary' AS parameter_scores,
  haiku_call_1_output->>'next_session_focus' AS what_we_told_you,
  annotated_frame_url
FROM form_analysis_results
WHERE user_id = $1
  AND exercise_id = $2
  AND id != $3
ORDER BY created_at DESC
LIMIT 1;
```

**Edge case:** If `next_session_focus` is null on the previous session (e.g. Call 1 failed to produce it), hide the "What we told you" section rather than showing an empty card.

---

## Action 4 — Fetch current session annotated frame

**What needs to happen:**
For the demo, the current session's annotated frame is not generated automatically by OpenCV. It is manually saved under `user_profile`. Fetch it from there.

**How to make it happen:**

```sql
SELECT annotated_frame_url
FROM user_profile
WHERE user_id = $1;
```

**Note:** This is a demo workaround. Post-demo, the annotated frame for the current session will come from `form_analysis_results` once OpenCV Part 2 is automated.

---

## Action 5 — Call Haiku and write output

**What needs to happen:**
Assemble the user prompt using current session data, previous session data, and user profile. Call Haiku. Write the output to `haiku_call_2_outputs`. Set `available = 1` on success or `available = 0` + `error` on failure.

**Output fields written by Haiku:**
- `progress_direction` — increase / maintain / decrease
- `weight_recommendation` — e.g. "Maintain at 12kg"
- `progression_verdict` — coach voice, max 120 chars
- `focus_this_week` — next session cue, max 120 chars
- `posture_trend` — short coaching observation sentence shown below posture score row on Progression tab, max 80 chars. TEXT, not an enum.
- `stability_trend` — same format, shown below stability score row, max 80 chars
- `range_of_motion_trend` — shown below range of motion score row, max 80 chars
- `movement_quality_trend` — shown below movement quality score row, max 80 chars
- `coaching_reasoning` — internal debug only, never shown to user

**How to make it happen:**
```
model:      claude-haiku-4-5-20251001
max_tokens: 1024
system:     cached system prompt
user:       assembled per-request prompt
```

On success → emit SSE: `haiku_call_2_complete`
On failure → emit SSE: `haiku_call_2_failed`, set `available = 0`, write error reason

---

## Action 6 — Render the Progression tab

**What needs to happen:**
When the user taps the Progression tab, show the right state based on what has arrived.

**SSE events to handle:**

| SSE Event | Frontend action |
|---|---|
| `haiku_call_2_no_history` | Show empty state: "No past sessions yet — come back after your next workout." |
| `haiku_call_2_complete` | Render full Progression tab |
| `haiku_call_2_failed` | Show fallback: "Progression analysis unavailable for this session." |

**How to make it happen — rendering sequence options:**

| Option | Description | Complexity | Recommendation |
|---|---|---|---|
| A — Wait for `haiku_call_2_complete` then render everything at once | Hold the tab in loading state until Haiku Call 2 finishes. Single render, no partial states. | Low. One loading state, one render. | **Recommended for demo.** Simplest to build, Call 2 is fast enough that the wait is not noticeable. |
| B — Render DB fields immediately, load Haiku fields in after | Show scores, frame images, and "What we told you" straight away. Progression verdict and trend fields drop in when Call 2 finishes. | Medium. Requires handling two render states and a partial loading indicator for the Haiku fields. | Better UX long term but adds frontend complexity. Consider post-demo. |
| C — Pre-fetch on tab load | Query all DB fields when the tab is tapped regardless of SSE. Haiku fields load when ready. | Medium-High. Requires managing DB + SSE state simultaneously. | Not recommended for demo. |

**Progression tab layout (when rendered):**

```
┌──────────────────────────────────┐
│  WHAT WE TOLD YOU                │  ← next_session_focus from previous session
├──────────────────────────────────┤
│  [prev frame]   [curr frame]     │  ← annotated frames side by side
│  prev weight    curr weight      │
│  prev date      curr date        │
├──────────────────────────────────┤
│  weight_recommendation           │  ← prominent
│  progression_verdict             │
├──────────────────────────────────┤
│  POSTURE                         │
│  [prev score] → [curr score]     │
│  posture_trend                   │
│                                  │
│  STABILITY                       │
│  [prev score] → [curr score]     │
│  stability_trend                 │
│                                  │
│  RANGE OF MOTION                 │
│  [prev score] → [curr score]     │
│  range_of_motion_trend           │
│                                  │
│  MOVEMENT QUALITY                │
│  [prev score] → [curr score]     │
│  movement_quality_trend          │
├──────────────────────────────────┤
│  FOCUS THIS WEEK                 │
│  focus_this_week                 │
└──────────────────────────────────┘
```

---

## What's Needed: Database Changes

### 1. Update `user_profile` table

Add the following fields:

| Field | Type | Purpose |
|---|---|---|
| `age` | INTEGER | Passed into Haiku Call 2 user prompt |
| `gender` | TEXT | Passed into Haiku Call 2 user prompt |
| `level` | TEXT | beginner / intermediate / advanced — used for progression logic |
| `injury_report` | BOOLEAN | Flag: does user have an injury history |
| `injury_details` | TEXT | Description of injury — passed into Haiku Call 2 user prompt |
| `annotated_frame_url` | TEXT | Demo workaround — current session frame (manually saved, since OpenCV is not automated for live uploads) |
| `ladder_url` | TEXT | Static dummy image (1 per user) for the progress graph on home screen and progression tab. Not dynamically generated for demo. |

---

### 2. Create `workout_session_logs` table

Tracks set-level workout data per session. Used by Haiku Call 2 to pull prior session history for the user prompt.

```sql
CREATE TABLE workout_session_logs (
  log_id          SERIAL PRIMARY KEY,
  user_id         TEXT NOT NULL,
  exercise_id     TEXT NOT NULL,
  session_id      TEXT NOT NULL,
  logged_at       TIMESTAMP DEFAULT NOW(),
  set_number      INTEGER,      -- which set: 1, 2, 3...
  weight_used     NUMERIC,      -- weight for this set
  reps_completed  INTEGER       -- reps performed in this set
);

CREATE INDEX idx_workout_logs_user ON workout_session_logs(user_id);
CREATE INDEX idx_workout_logs_session ON workout_session_logs(session_id);
```

**Demo note:** Dummy data for 3 demo users will be shared separately to be uploaded into this table. Developer does not need to generate this data.

---

## What's Needed: Assembling the Haiku Call 2 User Prompt

Three data sources are combined to fill the user prompt `{{placeholders}}` before each Haiku Call 2 request.

---

### How Data Assembly Works

When Haiku Call 1 finishes, it saves its output to the DB and sets its status to `completed`. S2's backend watches for that status change. When it fires, a **background function starts automatically** — this reuses the same async job pattern already in the pipeline.

That function runs four steps in sequence:

**Step 1 — Run 3 DB queries**
Three separate database calls, one per data source:
- Query 1 → `user_profile`: fetch level, age, gender, injury fields for this user
- Query 2 → `workout_session_logs`: fetch current + up to 2 prior sessions for this exercise
- Query 3 → `form_analysis_results`: fetch current + up to 2 prior form analyses for this exercise

These are standard SQL queries — same as any other DB call S2 already makes elsewhere in the pipeline.

**Step 2 — Fill the prompt template**
Take the user prompt template (the text with all `{{placeholders}}`) and substitute each placeholder with the actual value returned from the queries. This is string substitution in backend code — no special logic required.

**Step 3 — Call Haiku**
Send the fully assembled prompt to the Haiku API (`claude-haiku-4-5-20251001`, max_tokens: 1024). Receive JSON response.

**Step 4 — Write output and emit SSE**
Write Haiku's response fields to `haiku_call_2_outputs`. Set `available = 1`. Emit SSE event to frontend.

**On any failure** (DB query fails, Haiku call fails, JSON parse fails): set `available = 0`, write reason to `error` field, emit SSE so frontend knows to show fallback state.

---

---

### Block 1 — user_profile

| Table field | User prompt placeholder |
|---|---|
| `level` | `{{level}}` |
| `age` | `{{age}}` |
| `gender` | `{{gender}}` |
| `injury_report` | `{{active_pain}}` — yes / no |
| `injury_details` | `{{pain_detail}}` |

Query by `user_id`. Single row.

---

### Block 2 — workout_session_logs

Pull set-level data for the current session and up to 2 prior sessions for the same `exercise_id`, ordered by `logged_at` DESC.

Fields to pull per session: `session_id`, `logged_at`, `set_number`, `weight_used`, `reps_completed`

Group sets by `session_id` when assembling the prompt. Resulting structure per session:

```
Date: {{logged_at}}
Sets:
  Set 1 — {{weight_used}}kg × {{reps_completed}} reps
  Set 2 — {{weight_used}}kg × {{reps_completed}} reps
  ...
```

If fewer than 2 prior sessions exist for this `exercise_id`, send however many are available. If 0 prior sessions → emit `haiku_call_2_no_history`, do not call Haiku.

---

### Block 3 — form_analysis_results

Pull the following fields for the current session and up to 2 prior sessions, ordered by recency for the same `exercise_id`. If only 1 prior session exists, send 1.

| Field | How Haiku uses it |
|---|---|
| `overall_form_score` | Primary session quality signal. Read trend across 3 sessions. |
| `parameter_scores` | All 4 parameters: posture, stability, range_of_motion, movement_quality |
| `parameter.affirmation` | Per parameter — positive coaching context |
| `parameter.observation` | Per parameter — what was observed |
| `parameter.feedback` | Per parameter — actionable note |
| `per_rep_scores` | **Primary signal** for within-set degradation and RIR proxy. Compare first half vs last 2–3 reps. |
| `rep_trend_observation` | Call 1's narrative on rep pattern. Supporting context only — not a standalone signal. |
| `faults_detected` | List of faults identified this session. |
| `fault_details` | Detail per fault. Cross-reference across sessions for recurrence. |
| `fault_confidence` | high / medium / low per fault. Low confidence single session = watch, not confirmed. If same fault recurs across sessions, recurrence overrides low confidence — treat as confirmed. |
| `causal_chains` | Root cause per fault. If same root cause recurs across sessions, look at symptom trend (improving / flat / worsening) — that trajectory drives progression decision. Recurring unresolved root cause = do not increase weight. |
| `trends` | Slope data per metric across reps. Supporting signal — corroborates per-rep scores. Not a standalone signal. |
| `issue_tags` | Categorised fault tags for pattern matching across sessions. |

**Session selection logic:**
- Row 1: current `analysis_id`
- Row 2: most recent prior `analysis_id` by date, same `exercise_id`, same `user_id`
- Row 3: second most recent, same criteria
- If only 1 prior exists → send 1, omit Row 3
- If 0 prior exist → emit `haiku_call_2_no_history`, do not call Haiku

---

## SSE Events Summary

| Event | Trigger | Frontend response |
|---|---|---|
| `haiku_call_1_complete` | Call 1 saved to DB | Render Analysis tab, start waiting for Call 2 |
| `haiku_call_2_no_history` | No prior session found | Show empty state on Progression tab |
| `haiku_call_2_complete` | Call 2 output saved, `available = 1` | Render full Progression tab |
| `haiku_call_2_failed` | Call 2 errored, `available = 0` | Show fallback message on Progression tab |
