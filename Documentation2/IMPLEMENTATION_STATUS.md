# Implementation Status: What's Built vs What's Missing

**Purpose**: Single source of truth for current state of all features  
**Read Time**: 10-15 minutes  
**Audience**: All team members (plan next work based on this)  
**Last Updated**: June 24, 2026

---

## Executive Summary

| Status | Count | Impact |
|--------|-------|--------|
| ✅ **Fully Built** | 5 modules | Core product working |
| ⚠️ **Partially Built** | 2 modules | Gaps affecting usability |
| ❌ **Not Started** | 0 modules | (But 1 critical gap exists) |

### Critical Blocker
🔴 **Exercise Mapping table NOT built** - blocks Workout Builder feature

---

## ✅ FULLY BUILT & TESTED

### 1. User Profiles Module
**Status**: ✅ Complete  
**Completeness**: 100%

```
What's Built:
✅ User CRUD endpoints (POST, GET, PUT)
✅ Database schema (user_profiles table)
✅ Profile onboarding UI
✅ User data validation
✅ localStorage integration

No Known Gaps:
- All functionality working as expected
- Ready for production use
```

**Key Files**:
- `backend/routes/user.py`
- `frontend/src/pages/OnboardingPage.jsx`

**Database**:
```sql
user_profiles:
├─ user_id (UUID, PK)
├─ name, age, fitness_level
├─ goals, current_weight
├─ created_at, updated_at
└─ [All fields working]
```

---

### 2. Video Analysis Pipeline
**Status**: ✅ Complete  
**Completeness**: 100%

```
What's Built:
✅ Upload endpoint (POST /upload)
✅ GCS integration (video storage)
✅ File validation (MIME type, size)
✅ Database insert (form_analyses)
✅ Async background task spawn
✅ Quality gate logic
✅ MediaPipe integration
✅ Haiku Call 1 integration
✅ Haiku Call 2 integration
✅ SSE streaming (real-time progress)
✅ Error handling & logging

No Known Gaps:
- Pipeline fully operational end-to-end
- Handles concurrent uploads
- Graceful error handling
```

**Key Files**:
- `backend/routes/upload.py`
- `backend/pipeline/process_video.py`
- `frontend/src/pages/UploadScanPage.jsx`
- `frontend/src/pages/LoadingPage.jsx`

**Timeline**:
```
T=0-500ms:   Upload endpoint (returns analysis_id)
T=500-30s:   Quality gate + MediaPipe (async)
T=30-40s:    Haiku Call 1 (synchronous)
T=40s:       Tab 1 unlocks (form results)
T=40-50s:    Haiku Call 2 (async background)
T=50s:       Tab 2 unlocks (progression results)
```

---

### 3. MediaPipe Pose Detection
**Status**: ✅ Complete  
**Completeness**: 100%

```
What's Built:
✅ Pose landmarker initialization
✅ Frame-by-frame joint detection
✅ Angle calculations (knee, hip, trunk, ankle)
✅ Rep counting (bottom detection)
✅ Frame quality assessment
✅ Stability metrics (valgus, lateral shift, asymmetry)
✅ View detection (front vs side camera)
✅ Landmark quality thresholds
✅ Visualization (annotated frames)

Configuration:
✅ VISIBILITY_THRESHOLD = 0.70
✅ PRESENCE_THRESHOLD = 0.70
✅ Landmark importance weights (critical, important, least_impact)
✅ Per-camera-angle metric validity

No Known Gaps:
- All joint detections working
- Angles accurate
- Rep counts reliable
```

**Key Files**:
- `backend/mediapipe_code/landmark_framework.py`
- `backend/mediapipe_code/utils/landmark_quality_configuration.py`
- `backend/mediapipe_code/utils/angle_methods.py`

**Performance**:
```
Processing time: ~20-30 seconds per 10-second video
Frame rate: Every 3rd frame analyzed (10 fps effective)
Accuracy: Form scores align with manual review
```

---

### 4. Haiku Call 1 (Form Coaching)
**Status**: ✅ Complete  
**Completeness**: 100%

```
What's Built:
✅ Anthropic API integration
✅ System prompt (with exercise coaching reference)
✅ User message assembly (biomechanics + images)
✅ JSON parsing (response)
✅ Scoring logic:
  ├─ Range of Motion (35%)
  ├─ Stability (25%)
  ├─ Posture (25%)
  └─ Movement Quality (15%)
✅ Per-rep scoring
✅ Root cause analysis (RC1-RC5)
✅ Coaching output generation
✅ Next session focus recommendations
✅ Database storage (form_analysis_results)
✅ Error handling & retries

Tested on:
✅ Goblet Squat (3 exercises: goblet, barbell, deadlift)

No Known Gaps:
- Form scoring working accurately
- Coaching feedback is specific and actionable
- Rep-level analysis functional
```

**Key Files**:
- `backend/services/haiku_call_1_integration.py`
- `backend/prompts/haiku_call_1_system.txt`
- `backend/prompts/goblet_squat_coaching_reference.md`

**Output**:
```json
{
  "overall_form_score": 0-100,
  "rep_scores": [rep1, rep2, ...],
  "parameter_scores": {ROM, stability, posture, quality},
  "root_cause_analysis": [RC1, RC2, ...],
  "coaching_output": {affirm: [...], correct: [...]},
  "next_session_focus": [...]
}
```

**API Call**:
```
Model: claude-haiku-4-5-20251001
Tokens: ~2000 max
Time: 5-10 seconds
```

---

### 5. Haiku Call 2 (Progression Coaching)
**Status**: ✅ Complete  
**Completeness**: 100%

```
What's Built:
✅ Async background job spawning
✅ Current session fetching
✅ Previous session lookup (by exercise + user)
✅ Session comparison logic
✅ Weight progression rules:
  ├─ score >= 80 & improving → INCREASE (+2kg)
  ├─ score < 75 or dropped → HOLD (same)
  └─ dropped 8+ points → DECREASE (-2kg)
✅ Trend analysis per parameter
✅ JSON response generation
✅ Database storage (progression_results)
✅ SSE event emission
✅ Error handling & retries (1 + 3 retries)
✅ Rate limiting (SEMAPHORE = 1)
✅ No history detection (first-time users)

Tested on:
✅ Goblet Squat progression tracking
✅ Multiple sessions per user
✅ Weight progression rules

No Known Gaps:
- Session comparison working
- Weight recommendations accurate
- Trend analysis provides good insights
```

**Key Files**:
- `backend/services/haiku_call_2_progression.py`
- `backend/init_db.py:87-100` (progression_results schema)

**Output**:
```json
{
  "progress_direction": "up|down|stable",
  "weight_recommendation": {action, target_weight_kg, reason},
  "progression_verdict": "...",
  "posture_trend": "...",
  "stability_trend": "...",
  "range_of_motion_trend": "...",
  "movement_quality_trend": "..."
}
```

**Rate Limiting**:
```
HAIKU_CALL_2_SEMAPHORE = 1
├─ Only 1 job runs globally at a time
├─ Others queue up (acceptable for MVP)
└─ Can increase if needed
```

---

## ⚠️ PARTIALLY BUILT / HAS GAPS

### 6. Workout Builder & Logger
**Status**: ⚠️ Frontend only, no backend persistence  
**Completeness**: ~40% (frontend UI done, backend missing)

```
What's Built:
✅ Frontend UI (3 pages):
  ├─ WorkoutOrderPage.jsx: Select exercises, reorder
  ├─ ActiveWorkoutPage.jsx: Log sets/reps/weight
  └─ WorkoutLoggerPage.jsx: View past workouts
✅ localStorage persistence (works on single device)
✅ Form validation
✅ Basic UX flows

What's MISSING ❌:
❌ POST /workouts endpoint (create workout plan)
❌ GET /workouts endpoint (retrieve plans)
❌ POST /workouts/{id}/sessions endpoint (log workout)
❌ GET /workouts/history endpoint (view past)
❌ workouts database table
❌ Data persistence (currently lost on browser clear)
❌ Cross-device sync
❌ Exercise validation (currently hardcoded)

Current Problems:
├─ User loses data if browser cache cleared
├─ Can't sync between phone & desktop
├─ Can't add new exercises without code
└─ localStorage data not backed up
```

**Key Files** (Frontend - exists):
- `frontend/src/pages/UploadScanPage.jsx:6-13` (EXERCISES hardcoded)
- `frontend/src/pages/WorkoutOrderPage.jsx` (UI - localStorage)
- `frontend/src/pages/ActiveWorkoutPage.jsx` (UI - localStorage)
- `frontend/src/pages/WorkoutLoggerPage.jsx` (UI - localStorage)

**Key Files** (Backend - MISSING):
- `backend/routes/workouts.py` ❌ (doesn't exist)
- `backend/models/workouts.py` ❌ (doesn't exist)
- Database migrations ❌ (workouts table doesn't exist)

**Impact**:
- Users can plan workouts but data isn't saved durably
- Can't track workout history across devices
- Feature looks complete but is essentially non-functional

**Effort to Complete**:
- Create workouts table: 1 hour
- Implement 4 endpoints: 4-5 hours
- Frontend integration: 2-3 hours
- Database migrations: 1 hour
- **Total: 8-12 hours**

**Dependency**:
- ⛔️ BLOCKED by Exercise Mapping (needs master exercise table)
- Can't proceed until Exercise Mapping done

**What to Do**:
1. ❌ Don't start this yet
2. ⏳ Wait for Exercise Mapping
3. ⏭️ Then implement backend APIs

---

### 7. Exercise Mapping ❌
**Status**: ❌ Not started (CRITICAL BLOCKER)  
**Completeness**: 0%

```
Current State:
❌ No master exercises table
❌ Only 3 exercises hardcoded: goblet-squat, barbell-squat, deadlift
❌ Exercise IDs scattered: "goblet-squat" vs "goblet_squat" vs "ex_goblet_squat"
❌ No validation on exercise_id (any string accepted)
❌ No way to add exercises without code change
❌ Frontend hardcodes exercise list

What Needs Building:
1. Database Table: exercises
   ├─ exercise_id (PK)
   ├─ display_name
   ├─ muscle_group
   ├─ equipment
   ├─ haiku_model_name (for coaching prompt)
   ├─ coaching_cues (JSON)
   ├─ common_faults (JSON)
   └─ is_active (soft delete)

2. Seed Data:
   ├─ ex_goblet_squat / Goblet Squat / quads / ...
   ├─ ex_barbell_squat / Barbell Squat / quads / ...
   └─ ex_deadlift / Deadlift / glutes / ...

3. API Endpoint:
   ├─ GET /exercises → {QUADS: [...], GLUTES: [...], ...}
   └─ Used by workout builder & upload page

4. Frontend Integration:
   ├─ Stop hardcoding exercises
   ├─ Fetch from GET /exercises on mount
   └─ Keep in state

5. Data Cleanup:
   ├─ Migrate existing exercise_ids to standard format
   ├─ Add foreign key constraints
   └─ Validate all exercises exist in table

Impact (Why This is Blocker):
├─ 🔴 BLOCKS Workout Builder backend
├─ 🔴 BLOCKS adding new exercises
├─ 🟡 AFFECTS data integrity (no validation)
└─ 🟡 AFFECTS scalability (hardcoded limit)

Effort:
├─ Schema creation: 30 min
├─ Seed data: 30 min
├─ API endpoint: 1 hour
├─ Frontend integration: 1 hour
├─ Data migration & cleanup: 1 hour
└─ **Total: 4-6 hours**

Priority: 🔴 CRITICAL
```

**Files that will change**:
```
✅ backend/init_db.py (add exercises table)
✅ backend/routes/exercises.py (create new file)
✅ backend/scripts/seed_exercises.py (create new file)
✅ backend/scripts/migrate_exercise_ids.py (create new file)
✅ frontend/src/pages/UploadScanPage.jsx (fetch from API)
✅ frontend/src/pages/WorkoutOrderPage.jsx (fetch from API)
```

---

## Summary Table

| Module | Status | Built | Missing | Effort | Blocks |
|--------|--------|-------|---------|--------|--------|
| User Profiles | ✅ | 100% | — | Done | — |
| Video Analysis | ✅ | 100% | — | Done | — |
| MediaPipe | ✅ | 100% | — | Done | — |
| Haiku Call 1 | ✅ | 100% | — | Done | — |
| Haiku Call 2 | ✅ | 100% | — | Done | — |
| Workout Builder | ⚠️ | 40% | Backend | 8-12h | Exercise Mapping |
| Exercise Mapping | ❌ | 0% | All | 4-6h | Workout Builder |

---

## Critical Path: What Needs to Happen

### BEFORE Any New Feature Work

```
Priority 1: Exercise Mapping (4-6 hours)
├─ Create exercises table
├─ Seed 3 base exercises
├─ Create GET /exercises API
├─ Update frontend to fetch from API
└─ Migrate existing data
   ↓
   Unblocks: Workout Builder backend work

Priority 2: Workout Builder Backend (8-12 hours) [only after Priority 1]
├─ Create workouts table
├─ Implement 4 API endpoints
├─ Integrate with frontend
└─ Test end-to-end
   ↓
   Unblocks: Workout feature fully functional
```

### DONE - Don't Touch Unless Bugs
```
✅ User Profiles - stable, working
✅ Video Analysis - stable, working
✅ MediaPipe - stable, working
✅ Haiku Call 1 - stable, working
✅ Haiku Call 2 - stable, working
```

---

## When You Plan Next Sprint

**Ask These Questions**:

1. ✅ "Are we doing Exercise Mapping?" → If yes, allocate 4-6h
2. ✅ "Are we doing Workout Builder?" → If yes, Exercise Mapping MUST come first
3. ✅ "Are we fixing [module] bug?" → Check status above
4. ✅ "Are we adding new feature?" → Check blockers

---

## Known Limitations

### By Module

| Module | Known Limitation | Impact | Plan |
|--------|-----------------|--------|------|
| MediaPipe | Only tested on goblet/barbell/deadlift | Limited exercise coverage | Extend after Exercise Mapping |
| Haiku Call 1 | Coaching reference only for goblet_squat | Can't coach other exercises | Create refs for each exercise |
| Video Analysis | No video playback with coaching overlay | User can't see annotated video | Future phase |
| Workout Builder | Frontend only, data not persistent | Users lose data | Build backend (blocked) |
| Exercise Mapping | Doesn't exist | Can't add new exercises | START HERE |

---

## Testing Status

| Module | Manual Test | Automated Test | QA Approved |
|--------|-------------|-----------------|-------------|
| User Profiles | ✅ | ⚠️ Partial | ✅ |
| Video Analysis | ✅ | ✅ | ✅ |
| MediaPipe | ✅ | ⚠️ Partial | ✅ |
| Haiku Call 1 | ✅ | ⚠️ Partial | ✅ |
| Haiku Call 2 | ✅ | ⚠️ Partial | ✅ |
| Workout Builder | ✅ UI only | ❌ None | ⚠️ Partial |
| Exercise Mapping | N/A | N/A | N/A |

---

## Next Steps

1. **Decide**: Who owns Exercise Mapping?
2. **Schedule**: 4-6 hour block for Exercise Mapping work
3. **Then**: Plan Workout Builder backend work
4. **Finally**: Any other new features after these blockers are done

---

## Questions?

- **"What do I work on first?"** → Exercise Mapping (everything else is blocked or done)
- **"What's close to done?"** → Workout Builder (just needs backend)
- **"What's completely broken?"** → Nothing critical (all 5 core modules working)
- **"What's technical debt?"** → Exercise Mapping gap causes data integrity issues

---

**→ Ready to plan?** Share this status with your team and decide: Who's building Exercise Mapping, and when?

