# System Overview: Kinetic Architecture

**Purpose**: Understand the complete system design and how all pieces fit together  
**Read Time**: 30-45 minutes  
**Audience**: All developers (backend, frontend) + PMs

---

## What is Kinetic?

Kinetic is an **AI-powered fitness form analysis platform**. In one sentence:

> Users upload exercise videos. AI analyzes their form and recommends improvements + progressive overload.

---

## The 5 Core Flows

### Flow 1: User Onboarding
```
User lands on app
  ↓
Create profile (name, fitness level, goals)
  ↓
Database stores user_profiles
  ↓
✅ Ready to upload videos
```
**Owner**: User Profiles module  
**Status**: ✅ Fully built  
**Time**: ~30 seconds

---

### Flow 2: Video Upload & Analysis
```
User selects exercise & weight
  ↓
Records video (or uploads existing)
  ↓
Upload to GCS (Google Cloud Storage)
  ↓
[T=0.5s] Backend returns analysis_id immediately
  ↓
Backend spawns background task (user doesn't wait)
  ↓
[T=0.5-30s] Quality Gate: Is video clear enough?
  ├─ If NO → Return error, stop pipeline
  └─ If YES → Continue
  ↓
[T=2-30s] MediaPipe: Detect body joints from video
  ├─ Extract angles (knee, hip, trunk, ankle)
  ├─ Detect movements (squat depth, form breakdown)
  └─ Store in database
  ↓
[T=30s] Form analysis complete
```

**Owner**: Video Analysis module  
**Status**: ✅ Fully built  
**Time**: 30-60 seconds total (user waits ~500ms for response)

---

### Flow 3: Real-Time Form Coaching (Haiku Call 1)
```
After MediaPipe completes
  ↓
Assemble biomechanics data
  ├─ Frame-by-frame angle measurements
  ├─ 8 keyframe images (visual proof)
  ├─ Session metadata (weight, reps, pain level)
  └─ Exercise-specific coaching reference
  ↓
Call Claude Haiku API
  ↓
[T=30-40s] Haiku analyzes form:
  ├─ Scores each parameter (ROM, stability, posture, quality)
  ├─ Calculates per-rep form scores
  ├─ Identifies root causes (ankle restriction? glute weakness?)
  ├─ Generates coaching output (affirm + correct)
  └─ Recommends next session focus
  ↓
[T=40s] Store results in database
  ↓
[T=40.1s] Emit SSE event: "analysis_ready"
  ↓
✅ FRONTEND TAB 1 UNLOCKS
User immediately sees:
  • Form score: 74/100
  • Strengths: "Good depth, stable knees"
  • What to fix: "Reduce forward lean"
  • Next session: "3x8 with chest-up cue"
```

**Owner**: Haiku Call 1 module  
**Status**: ✅ Fully built  
**Time**: ~10 seconds (synchronous, part of main pipeline)  
**User sees**: Immediately on Tab 1

---

### Flow 4: Progression Coaching (Haiku Call 2)
```
After Haiku Call 1 completes
  ↓
Spawn background async job (doesn't block user)
  ↓
[T=40-50s] Meanwhile, user looking at Tab 1
  ↓
Haiku Call 2 background job:
  ├─ Fetch current session scores
  ├─ Query previous session (same exercise)
  │  └─ If NO previous → emit "no_history", done
  │  └─ If YES previous → continue
  ├─ Compare scores (up/down/stable?)
  ├─ Apply weight progression rules:
  │   • Score >= 80 & improving → INCREASE weight
  │   • Score < 75 or dropped → HOLD weight
  │   • Dropped 8+ points → DECREASE weight
  ├─ Analyze trends per parameter
  └─ Generate coaching output
  ↓
[T=50s] Store results in progression_results table
  ↓
[T=50.1s] Emit SSE event: "haiku_call_2_complete"
  ↓
✅ FRONTEND TAB 2 UNLOCKS
User sees:
  • "Great progress! +3 points since last session"
  • Weight recommendation: "Increase to 18kg"
  • Trend analysis: "Stability improving, ROM stable"
```

**Owner**: Haiku Call 2 module  
**Status**: ✅ Fully built  
**Time**: ~10 seconds (asynchronous, background job)  
**User sees**: Later on Tab 2 (doesn't block form feedback)

---

### Flow 5: Workout Planning & Logging ❌
```
User creates workout plan
  ├─ Select exercises (goblet squat, leg press, etc.)
  ├─ Reorder exercises
  └─ Set default reps/sets
  ↓
User performs workout
  ├─ Log sets/reps/weight for each exercise
  ├─ Record video for each set (optional)
  └─ Mark sets complete
  ↓
[BLOCKED] Backend persistence missing!
  ├─ Currently: Data stored in browser localStorage only
  ├─ Problem: Data lost on browser clear or device change
  ├─ Need: Backend APIs to store workout plans + sessions
  └─ Need: Exercise master table (currently hardcoded)
```

**Owner**: Workout Builder module  
**Status**: ⚠️ Frontend only, no backend  
**Blocker**: Exercise Mapping table, 4 backend API endpoints

---

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Pages:                                                            │
│  ├─ UploadScanPage: Select exercise, upload video               │
│  ├─ LoadingPage: Watch progress (SSE stream)                    │
│  ├─ ResultsPage: View form analysis (Tab 1) + progression (Tab 2) │
│  ├─ WorkoutOrderPage: Create workout plan (localStorage)         │
│  └─ WorkoutLoggerPage: Log sets/reps (localStorage)              │
│                                                                    │
│  API Calls:                                                        │
│  ├─ POST /upload (video)                                         │
│  ├─ GET /analysis/{id} (form results)                            │
│  ├─ GET /analysis/{id}/progression (progression results)         │
│  ├─ SSE stream /analysis/{id}/stream (real-time events)          │
│  └─ GET /exercises (exercise library - NOT YET IMPLEMENTED)      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                              ↕ API
┌────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Synchronous Path (blocks upload response):                       │
│  ├─ POST /upload                                                 │
│  │  ├─ Validate file                                             │
│  │  ├─ Upload to GCS                                             │
│  │  ├─ Create form_analyses record                               │
│  │  └─ Return analysis_id (500ms)                                │
│  └─ Spawn background task                                        │
│                                                                    │
│  Async Pipeline (doesn't block):                                  │
│  ├─ Quality Gate: Is video analyzable?                           │
│  ├─ MediaPipe: Detect body joints                                │
│  ├─ Haiku Call 1: Form coaching (5-10s)                          │
│  │  ├─ Score form (ROM 35%, stability 25%, posture 25%, quality 15%)
│  │  ├─ Root cause analysis                                       │
│  │  └─ Store in form_analysis_results                            │
│  └─ Emit SSE: "analysis_ready" (Tab 1 unlocks)                   │
│                                                                    │
│  Background Job (async, non-blocking):                            │
│  ├─ Haiku Call 2: Progression coaching (5-10s)                   │
│  │  ├─ Fetch previous session                                    │
│  │  ├─ Compare scores & apply weight rules                       │
│  │  ├─ Analyze trends                                            │
│  │  └─ Store in progression_results                              │
│  └─ Emit SSE: "haiku_call_2_complete" (Tab 2 unlocks)            │
│                                                                    │
│  Routes:                                                          │
│  ├─ POST /upload (submit video)                                  │
│  ├─ GET /analysis/{id} (form results)                            │
│  ├─ GET /analysis/{id}/progression (progression results)         │
│  ├─ GET /analysis/{id}/stream (SSE real-time events)             │
│  ├─ POST /users (create profile)                                 │
│  ├─ GET /users/{id} (get profile)                                │
│  └─ [TODO] POST /workouts, GET /workouts, etc.                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                              ↕ Database
┌────────────────────────────────────────────────────────────────────┐
│                   DATABASE (SQLite)                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Tables:                                                          │
│  ├─ user_profiles (user metadata)                                │
│  ├─ form_analyses (video upload metadata)                        │
│  ├─ form_analysis_results (form coaching output)                 │
│  ├─ progression_results (progression coaching output)            │
│  ├─ workout_sessions_log (set/rep logging)                       │
│  └─ [TODO] exercises (master exercise table)                     │
│  └─ [TODO] workouts (workout plans)                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                              ↕ External
┌────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ├─ Google Cloud Storage (video storage)                         │
│  ├─ MediaPipe (pose detection ML model)                          │
│  ├─ Anthropic API (Claude Haiku for AI coaching)                 │
│  └─ SSE (Server-Sent Events for real-time updates)               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Timeline: What Happens When User Uploads Video

```
T=0ms
├─ User selects exercise, weight, records/uploads video
└─ Clicks "Analyze"

T=0-500ms
├─ UPLOAD ENDPOINT (synchronous)
├─ Validate file (MIME type, size)
├─ Upload to GCS
├─ Create form_analyses record
└─ Return {"analysis_id": "abc-123"} to frontend

T=500ms ← USER GETS IMMEDIATE RESPONSE
├─ Frontend navigates to /loading page
├─ Shows "Analyzing your form..."
└─ Opens SSE stream: GET /analysis/abc-123/stream

T=500-1000ms
├─ Backend emits SSE: "upload_received" (10%)

T=1000-2000ms
├─ QUALITY GATE (evaluate video clarity)
├─ Check: Can we see body joints clearly?
├─ If NO → Return error SSE event, stop
├─ If YES → Continue

T=2000-30000ms
├─ MEDIAPIPE PROCESSING (most time-consuming)
├─ Process every 3rd frame to save time
├─ Detect 33 body joints per frame
├─ Extract angles: knee, hip, trunk, ankle
├─ Detect rep boundaries (bottom position)
├─ Backend emits: "mediapipe_started" (20%), "mediapipe_complete" (40%)

T=30000-40000ms
├─ HAIKU CALL 1 (Form Coaching)
├─ Assemble biomechanics JSON + 8 images
├─ Call Claude Haiku API
├─ Score form: ROM × 0.35 + Stability × 0.25 + Posture × 0.25 + Quality × 0.15
├─ Identify root causes
├─ Generate coaching output

T=40000ms ← TAB 1 UNLOCKS
├─ Store results in form_analysis_results
├─ Emit SSE: "analysis_ready" (80%)
├─ Frontend displays form score, strengths, fixes, next session focus
└─ User can read coaching immediately

T=40000-50000ms
├─ User reading Tab 1 results...
├─ Meanwhile, background task queues Haiku Call 2
├─ Emit SSE: "haiku_call_2_queued" (85%)

T=40000-50000ms (BACKGROUND)
├─ HAIKU CALL 2 (Progression Coaching)
├─ Fetch current session from database
├─ Query for previous session (same exercise)
├─ If NO previous → emit "no_history" (100%), done
├─ If YES → compare scores, apply weight rules
├─ Generate progression coaching

T=50000ms ← TAB 2 UNLOCKS
├─ Store results in progression_results
├─ Emit SSE: "haiku_call_2_complete" (100%)
├─ Frontend displays weight recommendation, trends
└─ User can see progression data

Total time: 50 seconds
User waits: 500 milliseconds
User sees form feedback: Immediately
User sees progression feedback: ~10 seconds later (async)
```

---

## Key Design Patterns

### 1. Async Pipeline (Don't Block User)

```python
# User uploads video
POST /upload → validate, GCS upload, DB insert → return immediately
    ↓ (user gets response in 500ms)
# Meanwhile, in background:
background_tasks.add_task(run_analysis_pipeline)
    ↓ (runs for 30-60s, user doesn't wait)
# Analysis happens, results stored in database
```

**Why**: User gets fast feedback (analysis_id), server can handle concurrent uploads.

---

### 2. SSE Streaming (Real-Time Progress)

Frontend opens persistent connection:
```javascript
const eventSource = new EventSource('/analysis/abc-123/stream')
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // Update progress: 10% → 20% → 40% → 80% → 100%
  updateProgressBar(data.percentage)
}
```

Backend emits events as pipeline progresses:
```python
await sse_manager.send_event(analysis_id, "mediapipe_started", 20)
await sse_manager.send_event(analysis_id, "analysis_ready", 80)
```

**Why**: Better UX than polling. User sees live progress.

---

### 3. Two Haiku Calls (Separate Concerns)

**Call 1 (Synchronous)**: "What's my form score right now?"
- Blocks pipeline (part of main analysis)
- Must complete before storing results
- User sees immediately

**Call 2 (Asynchronous)**: "Did I improve? Should I lift heavier?"
- Runs in background, doesn't block
- Needs previous session history (only found via async lookup)
- User sees later, doesn't matter if delayed

**Why**: Call 1 is critical path, Call 2 is nice-to-have. Separating them keeps feedback fast.

---

### 4. Quality Gate First

```python
# Before expensive processing:
if not passes_quality_gate(video):
    return {"error": "Video too dark/blurry, try again"}
# Only if passes:
run_mediapipe(video)  # Expensive!
run_haiku_call_1(biomechanics)
```

**Why**: Saves computation. Fails fast with actionable error.

---

## Modules Overview

| Module | Purpose | Status | Owner |
|--------|---------|--------|-------|
| User Profiles | User CRUD, onboarding | ✅ Built | [TBD] |
| Video Analysis | Upload pipeline, quality gate | ✅ Built | [TBD] |
| MediaPipe Processing | Pose detection, angle extraction | ✅ Built | [TBD] |
| Haiku Call 1 | Form coaching, scoring | ✅ Built | [TBD] |
| Haiku Call 2 | Progression coaching, weight recs | ✅ Built | [TBD] |
| Workout Builder/Logger | Workout planning & logging | ⚠️ Frontend only | [TBD] |
| Exercise Mapping | Master exercise table | ❌ Not built | [TBD] |

---

## 🔧 Technology Stack

### Currently in Use (Verified)

#### Backend

| Technology | Actual Version | Purpose |
|------------|--------|---------|
| **Python** | 3.14.3 | Runtime |
| **FastAPI** | 0.136.3 | Web framework |
| **Uvicorn** | 0.49.0 | ASGI server |
| **Pydantic** | 2.13.4 | Data validation |
| **Anthropic SDK** | 0.109.1 | Claude API client |
| **MediaPipe** | 0.10.35 | Pose detection (33 landmarks) |
| **OpenCV** | 4.13.0.92 | Video processing |
| **NumPy** | 2.4.6 | Numerical computing |
| **Pillow** | 12.2.0 | Image processing |
| **Google Cloud Storage** | 3.11.0 | Video storage |
| **databases** | 0.9.0 | Async DB abstraction |
| **aiosqlite** | 0.22.1 | Async SQLite |
| **python-dotenv** | 1.2.2 | Env config |
| **python-multipart** | 0.0.32 | Form data parsing |
| **SQLAlchemy** | 2.0.50 | ORM layer |
| **Matplotlib** | 3.10.9 | Visualization (debugging) |

#### Frontend

| Technology | Actual Version | Purpose |
|------------|--------|---------|
| **Node.js** | 24.14.0 (LTS) | Runtime |
| **npm** | 11.9.0 | Package manager |
| **React** | 18.3.1 | UI framework |
| **React Router** | 7.15.0 | Client routing |
| **Vite** | 5.4.10 | Build tool |
| **Lucide React** | 1.14.0 | Icon library |
| **Tailwind CSS** | 3.4.19 | Styling |
| **ESLint** | 9.13.0 | Code linting |
| **PostCSS** | 8.5.14 | CSS processing |
| **Autoprefixer** | 10.5.0 | CSS vendor prefixes |

#### External Services

| Service | Purpose |
|---------|---------|
| **Anthropic Claude API** | Form & progression coaching |
| **Google Cloud Storage** | Video upload & storage |
| **Google Cloud Platform** | Infrastructure |

#### Database

| Technology | Version | Purpose |
|------------|---------|---------|
| **SQLite** | 3.46+ (via aiosqlite) | Primary database |
| **databases** | 0.9.0 | Async DB abstraction layer |

---

### Planned for MVP Features (Not Yet Implemented)

You plan to add these technologies for upcoming features:

| Feature # | Technology | Purpose | Status |
|-----------|-----------|---------|--------|
| **#1: Auth** | Google OAuth SDK | Google Sign-In | Design phase |
| **#2: Exercises** | (None new) | Master exercises table | Design phase |
| **#3: Workout Backend** | (Current stack) | API endpoints + persistence | Blocked by #2 |
| **#4: RAG Injection** | LangChain, Sentence-Transformers, FAISS | Exercise content search | Planning |
| **Testing** | Pytest | Automated tests | Not started |
| **GPU Optimization** | Torch, CUDA/Metal | MediaPipe GPU support | Future |

---

### Key Architecture Notes

- **Database**: SQLite with `databases` abstraction layer for async access
- **Why SQLite**: Lightweight, no separate DB server needed, perfect for MVP phase
- **Version Pinning**: `requirements.txt` doesn't pin versions (uses compatible ranges). Consider pinning for production.
- **Why minimal tech debt**: Core system is intentionally lightweight to allow team flexibility when adding MVP features.
- **Verification**: These versions were verified against actual `pip list` and `package.json` as of June 25, 2026.

---

## What's Next

Before building anything new, refer to [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) to understand:
- What's fully complete
- What has gaps
- What's blocking new work

---

**→ Next**: Read [ARCHITECTURE/DECISIONS.md](./DECISIONS.md) to understand *why* we made these architectural choices.

