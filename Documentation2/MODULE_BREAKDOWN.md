# Module Breakdown: Who Owns What

**Purpose**: Understand module ownership, dependencies, and integration points  
**Read Time**: 10-15 minutes  
**Audience**: All developers (prevent duplicate work, understand who to ask)

---

## Module Ownership & Status

| # | Module | Owner | Status | Key Files |
|---|--------|-------|--------|-----------|
| 1 | User Profiles | [TBD] | ✅ Built | `routes/user.py` |
| 2 | Video Analysis | [TBD] | ✅ Built | `routes/upload.py`, `pipeline/process_video.py` |
| 3 | MediaPipe Processing | [TBD] | ✅ Built | `mediapipe_code/landmark_framework.py` |
| 4 | Haiku Call 1 | [TBD] | ✅ Built | `services/haiku_call_1_integration.py` |
| 5 | Haiku Call 2 | [TBD] | ✅ Built | `services/haiku_call_2_progression.py` |
| 6 | Workout Builder/Logger | [TBD] | ⚠️ Partial | `UploadScanPage.jsx`, `ActiveWorkoutPage.jsx` |
| 7 | Exercise Mapping | [TBD] | ❌ Not built | [TODO] |

---

## Module Details

### 1️⃣ User Profiles Module

**What it does**: User CRUD (Create, Read, Update), onboarding  
**Owner**: [TBD]  
**Status**: ✅ Fully built & tested

**Key files**:
- `backend/routes/user.py` - API endpoints
- `backend/init_db.py:1-30` - `user_profiles` table schema
- `frontend/src/pages/OnboardingPage.jsx` - UI

**Endpoints**:
- `POST /users` - Create new user
- `GET /users/{id}` - Get user profile
- `PUT /users/{id}` - Update profile

**Database**:
```sql
user_profiles:
├─ user_id (UUID, primary key)
├─ name, age, fitness_level
├─ goals, current_weight
└─ created_at, updated_at
```

**Dependencies**:
- None (foundation module)

**Dependents**:
- Every other module (all track user_id)

**Integration Points**:
- User selects profile → starts using app
- Video analysis stores user_id
- Progression tracking filters by user_id

**If you're touching this**:
- Contact: [TBD - module owner]
- Be careful: user_id is referenced everywhere
- Note: Frontend stores user_id in localStorage

---

### 2️⃣ Video Analysis Module

**What it does**: Accept video uploads, store in cloud, orchestrate pipeline  
**Owner**: [TBD]  
**Status**: ✅ Fully built & tested

**Key files**:
- `backend/routes/upload.py` - Upload endpoint
- `backend/pipeline/process_video.py` - Pipeline orchestration
- `frontend/src/pages/UploadScanPage.jsx` - Upload UI

**Endpoints**:
- `POST /upload` - Submit video (returns analysis_id in 500ms)
- `GET /analysis/{id}/stream` - SSE stream for real-time progress

**Pipeline stages**:
1. File validation (MIME type, size)
2. GCS upload (Google Cloud Storage)
3. Database insert (form_analyses record)
4. ← User gets response here
5. Quality gate (async background task starts)
6. MediaPipe processing
7. Haiku Call 1
8. Haiku Call 2

**Dependencies**:
- MediaPipe module (pose detection)
- Haiku Call 1 module (form coaching)
- Haiku Call 2 module (progression coaching)

**Dependents**:
- Frontend (initiates uploads)

**Integration Points**:
- Takes user_id, exercise, weight from frontend
- Passes biomechanics to Haiku Call 1
- Stores results in database
- Emits SSE events for progress

**If you're touching this**:
- Contact: [TBD - module owner]
- Note: Critical path - changes affect all downstream
- Warning: This is where the async magic happens

---

### 3️⃣ MediaPipe Processing Module

**What it does**: Detect body joints from video, extract angles  
**Owner**: [TBD]  
**Status**: ✅ Fully built & tested

**Key files**:
- `backend/mediapipe_code/landmark_framework.py` - Main processor
- `backend/mediapipe_code/utils/landmark_quality_configuration.py` - Config
- `backend/mediapipe_code/utils/angle_methods.py` - Angle calculations

**What it calculates**:
- 33 body joint positions (x, y, z coordinates)
- Angles: knee, hip, trunk, ankle, etc.
- Rep counts and boundaries
- Stability metrics (valgus, lateral shift, asymmetry)
- Per-frame quality assessment

**Configuration** (in landmark_quality_configuration.py):
- VISIBILITY_THRESHOLD: 0.70
- PRESENCE_THRESHOLD: 0.70
- Landmark importance weights (critical, important, least_impact)

**Dependencies**:
- MediaPipe ML model (pre-trained, external)

**Dependents**:
- Haiku Call 1 (uses angle data)
- Video Analysis (calls this from pipeline)

**Integration Points**:
- Receives: Local video file path
- Returns: JSON with frame-by-frame angles + aggregates
- Emits: SSE event "mediapipe_started" / "mediapipe_complete"

**If you're touching this**:
- Contact: [TBD - module owner]
- Warning: Complex math (angles, geometry) - test thoroughly
- Note: Frame rate is set here (processes every 3rd frame)
- Consider: Changes to thresholds affect quality gate for ALL exercises

---

### 4️⃣ Haiku Call 1 Module

**What it does**: Real-time form analysis & coaching  
**Owner**: [TBD]  
**Status**: ✅ Fully built & tested

**Key files**:
- `backend/services/haiku_call_1_integration.py` - Main integration
- `backend/prompts/haiku_call_1_system.txt` - System prompt template
- `backend/prompts/goblet_squat_coaching_reference.md` - Exercise knowledge

**What it does**:
1. Assembles biomechanics + images into prompt
2. Calls Claude Haiku API
3. Parses JSON response
4. Stores in form_analysis_results table

**Input data**:
- Session metadata (exercise, weight, reps, camera angle)
- Biomechanics JSON (angles per frame + aggregates)
- 8 keyframe images (visual proof)
- Coaching reference (exercise-specific knowledge)

**Output data**:
```json
{
  "overall_form_score": 74,
  "rep_scores": [{rep_number, form_score, parameter_breakdown}, ...],
  "parameter_scores": {
    "range_of_motion": {score, affirmation, observation, correction},
    "stability": {...},
    "posture": {...},
    "movement_quality": {...}
  },
  "root_cause_analysis": [{id, name, severity, affected_reps, evidence}, ...],
  "coaching_output": {affirm: [...], correct: [...]},
  "next_session_focus": [...]
}
```

**Scoring weights**:
- Range of Motion: 35%
- Stability: 25%
- Posture: 25%
- Movement Quality: 15%

**Dependencies**:
- Anthropic API (Claude Haiku)
- MediaPipe output (biomechanics)

**Dependents**:
- Video Analysis pipeline (calls this)
- Haiku Call 2 (uses the scores)
- Frontend Tab 1 (displays results)

**Integration Points**:
- Triggered by: Video Analysis after MediaPipe completes
- Calls: `claude-haiku-4-5-20251001` model
- Stores: In form_analysis_results table
- Emits: SSE event "analysis_ready"

**If you're touching this**:
- Contact: [TBD - module owner]
- Warning: Changes to scoring logic affect all users
- Note: System prompt includes exercise-specific coaching reference
- Consider: Need to add new exercise? Must create coaching reference markdown

---

### 5️⃣ Haiku Call 2 Module

**What it does**: Progression coaching & weight recommendations  
**Owner**: [TBD]  
**Status**: ✅ Fully built & tested

**Key files**:
- `backend/services/haiku_call_2_progression.py` - Main implementation
- `backend/init_db.py:87-100` - progression_results table schema

**What it does**:
1. Fetches current session scores
2. Queries for previous session (same exercise)
3. Compares and applies weight progression rules
4. Calls Haiku for trend analysis
5. Stores results in progression_results table

**Weight Progression Logic**:
```
IF overall_form_score >= 80 AND improving
  → INCREASE weight (+2kg)
  
ELSE IF overall_form_score < 75 OR dropped
  → HOLD weight (same kg)
  
ELSE IF dropped significantly (8+ points)
  → DECREASE weight (-2kg)
```

**Output data**:
```json
{
  "progress_direction": "up|down|stable",
  "weight_recommendation": {
    "action": "hold|increase|decrease",
    "target_weight_kg": 18.0,
    "reason": "..."
  },
  "progression_verdict": "...",
  "posture_trend": "...",
  "stability_trend": "...",
  "range_of_motion_trend": "...",
  "movement_quality_trend": "..."
}
```

**Dependencies**:
- Anthropic API (Claude Haiku)
- Haiku Call 1 (uses the scores)
- Database (previous session lookup)

**Dependents**:
- Video Analysis pipeline (spawns this)
- Frontend Tab 2 (displays results)

**Integration Points**:
- Triggered by: Video Analysis after Haiku Call 1 completes
- Fetches: Current + previous form_analysis_results
- Calls: `claude-haiku-4-5-20251001` model
- Stores: In progression_results table
- Emits: SSE event "haiku_call_2_complete" or "haiku_call_2_no_history"

**If you're touching this**:
- Contact: [TBD - module owner]
- Note: This is async, doesn't block user
- Warning: Weight progression rules are critical - test weight recommendations
- Consider: First-time users have no previous session (graceful "no_history")
- Rate limiting: HAIKU_CALL_2_SEMAPHORE limits to 1 concurrent call globally

---

### 6️⃣ Workout Builder & Logger Module

**What it does**: Plan workouts, log sets/reps, view history  
**Owner**: [TBD]  
**Status**: ⚠️ Frontend only, no backend

**Current Implementation**:
- ✅ `UploadScanPage.jsx` - Select exercise, reorder
- ✅ `ActiveWorkoutPage.jsx` - Log sets/reps/weight
- ✅ `WorkoutLoggerPage.jsx` - View past workouts
- ✅ localStorage persistence (works on single device)

**What's Missing** ❌:
- Backend endpoints (POST /workouts, GET /workouts, etc.)
- Database table (workouts)
- Database persistence (data lost on browser clear)
- Cross-device sync (mobile + web)
- Exercise validation (currently hardcoded)

**Blocker**: Depends on Exercise Mapping module (need master exercise table)

**Impact**:
- Users lose workout data if they clear browser cache
- Data doesn't sync across devices
- Can't add new exercises without code change

**Effort to complete**: 8-12 hours

**If you're touching this**:
- Contact: [TBD - module owner]
- First: Wait for Exercise Mapping to be built
- Then: Implement 4 backend endpoints + database migrations

---

### 7️⃣ Exercise Mapping Module

**What it does**: Master exercises table, exercise library  
**Owner**: [TBD]  
**Status**: ❌ Not started (Critical blocker!)

**Current Problem**:
- Only 3 exercises hardcoded: goblet-squat, barbell-squat, deadlift
- Exercise IDs scattered across code (no validation)
- No way to add new exercises without code changes
- Data integrity issues (any string accepted as exercise_id)

**What Needs Building**:
1. Database table: exercises
   ```sql
   CREATE TABLE exercises (
     exercise_id TEXT PRIMARY KEY,
     display_name TEXT,
     muscle_group TEXT,
     equipment TEXT,
     haiku_model_name TEXT,
     coaching_cues TEXT (JSON),
     common_faults TEXT (JSON),
     is_active BOOLEAN
   )
   ```

2. Seed initial exercises
   ```sql
   INSERT INTO exercises VALUES
     ('ex_goblet_squat', 'Goblet Squat', 'quads', ...),
     ('ex_barbell_squat', 'Barbell Squat', 'quads', ...),
     ('ex_deadlift', 'Deadlift', 'glutes', ...)
   ```

3. API endpoint: `GET /exercises`
   ```json
   Returns exercises grouped by muscle group
   ```

4. Frontend: Fetch from backend instead of hardcoded

5. Data migration: Fix existing exercise_id references

**Effort**: 4-6 hours

**Blocks**:
- ✋ Workout Builder (needs exercise library)
- ✋ Any new exercise support

**If you're touching this**:
- Contact: [TBD - module owner]
- Note: This is highest priority blocker
- Impact: Every other feature depends on this
- Start here before Workout Builder backend

---

## Dependencies Visualization

```
User Profiles (foundation)
  ↓
  ├─ Video Analysis
  │  ├─ MediaPipe Processing
  │  ├─ Haiku Call 1 ← outputs to Tab 1
  │  └─ Haiku Call 2 ← outputs to Tab 2
  │
  ├─ Workout Builder ← BLOCKS on Exercise Mapping
  │  └─ Exercise Mapping ← CRITICAL BLOCKER
  │
  └─ Exercise Mapping
     ↑ (needed by Workout Builder)
```

---

## "If You're Working on X, Talk to Y"

| If you're building | Talk to | Because |
|-------------------|---------|---------|
| New exercise support | Exercise Mapping owner | Need to add to master table |
| New scoring logic | Haiku Call 1 owner | Changes affect all users |
| Weight progression rules | Haiku Call 2 owner | Changes affect load recommendations |
| Video quality issues | MediaPipe owner | Quality thresholds live here |
| Frontend integrations | Video Analysis owner | Data flow coordination |
| Workout features | Exercise Mapping owner first, then Workout Builder owner | Exercise Mapping is blocker |

---

## Key Constraints & Notes

### Rate Limiting
- Haiku Call 2 has SEMAPHORE(1) - only 1 concurrent job globally
- Why: Prevent hammering Anthropic API
- Impact: If 10 users upload at once, Call 2 queues up

### Data Contracts
- **form_analyses** → **form_analysis_results**: 1:1 relationship (one result per analysis)
- **form_analysis_results** → **progression_results**: 1:1 relationship
- **form_analyses** → **progression_results**: 1:1 relationship

### Exercise ID Format
- Current inconsistency: "goblet-squat" vs "goblet_squat" vs "ex_goblet_squat"
- After Exercise Mapping: Standardized to "ex_goblet_squat" format
- Will add database constraints to prevent bad data

---

## Next Document

→ Read [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) to see exactly what's built, what's missing, and what's blocking new work.

