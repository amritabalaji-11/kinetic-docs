# Kinetic Data Foundation

## Overview
This document defines the core data schemas for exercises, users, and sessions in Kinetic. 
- **Database**: Supabase (PostgreSQL)
- **Exercise ID Convention**: `{category}_{sequence}_{exercise_name}` (e.g., `leg_001_goblet`)
- **User ID Strategy**: 3 hardcoded user IDs based on profile selection (no UUID generation)
- **Scope**: Starting with Goblet Squat (MVP), designed to scale to RDL and beyond.

---

## 1. Exercise Definitions

### Schema
```
Exercise {
  id: string                    // Unique identifier (e.g., "goblet-squat-v1")
  name: string                  // Human-readable name
  slug: string                  // URL-friendly identifier (e.g., "goblet-squat")
  category: string              // Exercise category (e.g., "lower-body", "compound")
  difficulty: number            // 1-5 scale (1=beginner, 5=advanced)
  description: string           // Brief description of the exercise
  primary_muscles: string[]     // Main muscle groups targeted
  secondary_muscles: string[]   // Secondary muscles engaged
  equipment: string[]           // Required equipment (e.g., ["dumbbell", "kettlebell"])
  created_at: timestamp         // When exercise was added to system
}
```

### Examples

**Goblet Squat**
```
id: "leg_001_goblet"
name: "Goblet Squat"
slug: "goblet-squat"
category: "lower-body"
difficulty: 2
description: "Squat holding a weight at chest level. Excellent for beginners, improves posture and knee tracking."
primary_muscles: ["quadriceps", "glutes"]
secondary_muscles: ["hamstrings", "core", "upper-back"]
equipment: ["kettlebell", "dumbbell"]
```

**Romanian Deadlift (RDL)** — Future
```
id: "leg_002_rdl"
name: "Romanian Deadlift"
slug: "rdl"
category: "lower-body"
difficulty: 3
description: "Hip-hinge movement targeting posterior chain. Requires understanding of proper form."
primary_muscles: ["hamstrings", "glutes"]
secondary_muscles: ["lower-back", "upper-back"]
equipment: ["barbell", "dumbbell"]
```

---

## 2. User Schema

### Core User Profile
```
User {
  id: string                    // Hardcoded user ID (one of 3 options below)
  email: string                 // User's email address (unique)
  name: string                  // Display name
  profile_type: string          // Profile selection: "beginner" | "intermediate" | "advanced"
  created_at: timestamp         // Account creation date
  updated_at: timestamp         // Last profile update
}
```

### Hardcoded User IDs (For Demo)
| User ID | Email | Name | Notes |
|---------|-------|------|-------|
| `user_001` | user001@demo.kinetic | (Real user video) | Goblet squat real video run through MediaPipe + Haiku Call 1 |
| `user_002` | user002@demo.kinetic | (Real user video) | Goblet squat real video run through MediaPipe + Haiku Call 1 |
| `user_003` | user003@demo.kinetic | (Real user video) | Goblet squat real video run through MediaPipe + Haiku Call 1 |

**Backend Instructions:**
- Do NOT generate UUIDs for user creation
- Use only these 3 hardcoded IDs: `user_001`, `user_002`, `user_003`
- Each ID can only exist once in the system
- Email field is required and unique per ID
- Pre-populate with real video analysis results (see Pre-Seeded Session Data below)

### User Fitness Profile
```
UserFitnessProfile {
  user_id: string               // Reference to User
  experience_level: string      // "beginner", "intermediate", "advanced"
  age: number                   // (optional)
  height_cm: number             // (optional) For form analysis context
  weight_kg: number             // (optional) For load recommendations
  injuries: string[]            // (optional) List of current injuries/restrictions
  goals: string[]               // ["strength", "endurance", "hypertrophy", "mobility"]
  available_equipment: string[] // Equipment at their location
  updated_at: timestamp
}
```

### User → Exercise Mapping
```
UserExerciseProgress {
  id: string                    // Unique tracking ID
  user_id: string               // Reference to User
  exercise_id: string           // Reference to Exercise
  first_attempted: timestamp    // When user first did this exercise
  personal_best: object         // Best recorded performance
    {
      value: number             // e.g., reps, weight, time
      unit: string              // e.g., "reps", "kg", "seconds"
      date: timestamp
    }
  last_session: timestamp       // Last time user performed exercise
  total_sessions: number        // How many times they've done it
}
```

### Example User Instance

**User: Alice (Beginner Profile)**
```
User:
  id: "user_beginner_001"
  email: "alice@example.com"
  name: "Alice Johnson"
  profile_type: "beginner"
  created_at: 2026-05-01
  
UserFitnessProfile:
  user_id: "user_beginner_001"
  experience_level: "beginner"
  height_cm: 165
  weight_kg: 68
  goals: ["strength", "mobility"]
  available_equipment: ["kettlebell", "dumbbell"]
  
UserExerciseProgress (Goblet Squat):
  id: "progress_beginner_goblet_001"
  user_id: "user_beginner_001"
  exercise_id: "leg_001_goblet"
  first_attempted: 2026-05-10
  personal_best: { value: 24, unit: "reps", date: 2026-05-24 }
  last_session: 2026-05-25
  total_sessions: 8
```

---

## 3. Session/Workout Data

### Session Recording
```
WorkoutSession {
  id: string                    // Unique session ID
  user_id: string               // Which user
  exercise_id: string           // Which exercise
  date: timestamp               // When performed
  
  performance_data: object
    {
      reps: number              // (if applicable)
      weight_kg: number         // (if applicable)
      duration_seconds: number  // (if applicable)
      perceived_difficulty: number // 1-10 scale
      notes: string             // User notes
    }
    
  form_analysis: object         // Output from vision analysis
    {
      range_of_motion_score: number // 0-100
      alignment_score: number       // 0-100 (knee tracking, spine, etc.)
      tempo_consistency: number     // 0-100
      issues_detected: string[]     // ["excessive-knee-valgus", "limited-depth"]
    }
}
```

### Example Session

**Alice's Goblet Squat Session (2026-05-25)**
```
id: "session_beginner_goblet_20260525"
user_id: "user_beginner_001"
exercise_id: "leg_001_goblet"
date: 2026-05-25T10:30:00Z

performance_data:
  reps: 24
  weight_kg: 12
  perceived_difficulty: 6
  notes: "Felt good, could do more"

form_analysis:
  range_of_motion_score: 78
  alignment_score: 82
  tempo_consistency: 85
  issues_detected: ["slight-forward-lean"]
```

---

## 4. Data Relationships & Demo User Flow

```
User (1) ──── (many) UserFitnessProfile
User (1) ──── (many) UserExerciseProgress
User (1) ──── (many) WorkoutSession

Exercise (1) ──── (many) UserExerciseProgress
Exercise (1) ──── (many) WorkoutSession
```

### Demo User Selection Flow

```
Frontend (App Launch)
    ↓
Profile Selection Screen (3 hardcoded options)
    ├─ "Beginner" card → select
    ├─ "Intermediate" card → select
    └─ "Advanced" card → select
    ↓
User Selects Profile (e.g., "Beginner")
    ↓
Frontend stores: user_id = "user_beginner_001" in sessionStorage
    ↓
ALL subsequent API calls include header: { "user_id": "user_beginner_001" }
    ↓
Backend reads header, queries DB for user_beginner_001's sessions & data
    ↓
Dashboard loads: form_analysis_results + progression data for user_beginner_001
```

**Key point:** No dynamic mapping. Each profile card is hardcoded to a specific user_id. Selection is just: user picks card → frontend uses that card's ID on every request.

---

### Pre-Seeded Session Data (Real User Videos)

**Process:** Film 2–3 real users performing Goblet Squat. Run each video through the full pipeline (MediaPipe + Haiku Call 1). Save real analysis results to the DB for each user.

**What this gives the demo:**
- Real form analysis output (not dummy scores)
- Real coaching feedback from Haiku Call 1
- Real biomechanics JSON with actual joint angles
- Real annotated frame showing user's worst rep with corrections

**For each user (user_001, user_002, user_003):**
1. Record 1 high-quality Goblet Squat video (8–10 reps)
2. Run through MediaPipe → extract landmarks + quality gate pass
3. Run through Biomechanics script → calculate angles per rep
4. Run through OpenCV Part 1 → generate 8-frame composite
5. Run through Haiku Call 1 → get form scores + coaching + rep breakdown
6. Run through OpenCV Part 2 → extract worst rep, annotate with angles
7. Save all outputs to form_analysis_results table
8. User selection on demo → dashboard shows this real analysis

**Why this matters:** Real data is infinitely more credible than dummy data. When investor clicks on a session, they see actual form analysis on an actual person—immediately proves the product works.

---

### Biomechanics JSON → OpenCV Frame Extraction Data Flow

**Step 1: Biomechanics Script Output (Squad 3)**

Biomechanics script processes landmarks per frame and outputs JSON per rep:

```json
{
  "rep_1": {
    "knee_angle": 88.2,
    "hip_angle": 86.5,
    "ankle_dorsiflexion": 22.1,
    "tempo_seconds": 1.37,
    "bottom_frame": 42,              // Frame number where user is at lowest point
    "bottom_timestamp_ms": 1400      // Milliseconds into video (42 frames ÷ 30fps ≈ 1400ms)
  },
  "rep_2": {
    "knee_angle": 85.0,
    "hip_angle": 87.2,
    "ankle_dorsiflexion": 23.5,
    "tempo_seconds": 1.41,
    "bottom_frame": 84,
    "bottom_timestamp_ms": 2800
  },
  // ... more reps
}
```

**Saved to:** `form_analysis_results` table in DB

---

**Step 2: Haiku Call 1 Scoring (Squad 2)**

Haiku Call 1 receives the biomechanics JSON + 8-frame composite and outputs:

```json
{
  "overall_score": 72,
  "per_rep_scores": [78, 79, 68, 74, 71],  // Score for each rep
  "worst_rep_index": 2,                     // Rep 3 (index 2) scored 68 — the lowest
  "coaching": "Your ankle dorsiflexion is limiting depth..."
}
```

**Saved to:** `form_analysis_results` table in DB

---

**Step 3: OpenCV Part 2 Frame Extraction (Squad 3) — THE CRITICAL HANDOFF**

OpenCV Part 2 needs to extract and annotate the worst-performing rep:

```
OpenCV Part 2 Logic:
  1. Read worst_rep_index from Haiku output → "2" (rep 3)
  2. Read biomechanics JSON from form_analysis_results
  3. Look up rep_2 (index 2) in JSON → get bottom_timestamp_ms = 2800
  4. Seek raw video to 2800ms (or 84 frames at 30fps)
  5. Extract frame at that timestamp
  6. Draw skeleton overlay from MediaPipe landmarks
  7. Add angle values: "Knee: 85°", "Hip: 87.2°", "Ankle: 23.5°"
  8. Add gold standard reference lines: "Ideal: 80–95°"
  9. Color code: green (in range), amber (borderline), red (out of range)
  10. Save annotated JPEG to GCS
  11. Return annotated_frame_url to frontend via SSE
```

**Data flow visualized:**

```
form_analysis_results table (after Steps 1–2)
    ├─ biomechanics_json (full JSON with bottom_timestamp_ms per rep)
    └─ haiku_call_1_output (per_rep_scores[], worst_rep_index)
         ↓
    OpenCV Part 2 reads both
         ↓
    Extracts frame at bottom_timestamp_ms for worst rep
         ↓
    Annotates with angles + gold standard
         ↓
    Saves: annotated_frame_url to form_analysis_results
         ↓
    SSE event: frame_ready
         ↓
    Frontend displays on Results screen (Tab 1)
```

**Key question for clarification:** When OpenCV Part 2 looks up `bottom_timestamp_ms`, does it extract the frame directly from the raw video file in GCS, or from the overlay video saved in Step 5? (Raw video is cleaner, but overlay video already has skeleton drawn.)

---

## 5. Key Design Decisions

| Decision | Why | Impact |
|----------|-----|--------|
| **Exercise versioning** (e.g., "goblet-squat-v1") | Allows form changes/cue updates over time without breaking history | Users can track improvements as we refine teaching |
| **Separate UserFitnessProfile** | Not all users provide detailed profile info; keeps User table clean | Flexible onboarding (can skip injury/goal details initially) |
| **range_of_motion_score** | Core metric for Goblet Squat; directly tied to form quality | Enables progression tracking and form feedback |
| **Timestamped records** | Every data point includes when it happened | Can show trends, analyze improvement over weeks |
| **Form analysis separate from performance** | Not all exercises need vision analysis initially (e.g., basic tracking) | Scales: add vision analysis later for new exercises |

---

## 6. Supabase Table Schemas

### Users Table
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,                    -- "user_beginner_001", "user_intermediate_001", etc.
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  profile_type TEXT NOT NULL,             -- "beginner" | "intermediate" | "advanced"
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Demo data insert (real users with real video analysis)
INSERT INTO users (id, email, name, profile_type) VALUES
  ('user_001', 'user001@demo.kinetic', 'User 1 (Real Video)', 'demo'),
  ('user_002', 'user002@demo.kinetic', 'User 2 (Real Video)', 'demo'),
  ('user_003', 'user003@demo.kinetic', 'User 3 (Real Video)', 'demo');
```

### Exercises Table
```sql
CREATE TABLE exercises (
  id TEXT PRIMARY KEY,                    -- "leg_001_goblet"
  name TEXT NOT NULL,
  slug TEXT UNIQUE,
  category TEXT,                          -- "lower-body", "upper-body", etc.
  difficulty INT,                         -- 1-5
  description TEXT,
  primary_muscles TEXT[],
  secondary_muscles TEXT[],
  equipment TEXT[],
  created_at TIMESTAMP DEFAULT NOW()
);

-- Demo data insert
INSERT INTO exercises (id, name, slug, category, difficulty, description, primary_muscles, secondary_muscles, equipment) VALUES
  ('leg_001_goblet', 'Goblet Squat', 'goblet-squat', 'lower-body', 2, 
   'Squat holding a weight at chest level. Excellent for beginners, improves posture and knee tracking.',
   ARRAY['quadriceps', 'glutes'], 
   ARRAY['hamstrings', 'core', 'upper-back'],
   ARRAY['kettlebell', 'dumbbell']);
```

### User Profiles Table (HOME SCREEN DATA)
```sql
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT UNIQUE NOT NULL REFERENCES users(id),
  experience_level TEXT,                  -- "beginner", "intermediate", "advanced"
  
  -- HOME SCREEN — Dummy/Backup Images (from design)
  progression_graph_url TEXT,             -- GCS/Supabase Storage URL for weight trend chart
  calendar_heatmap_url TEXT,              -- GCS/Supabase Storage URL for session calendar
  progression_graph_image_key TEXT,       -- e.g., "dummy/user_beginner_001_progress_ladder.png"
  calendar_heatmap_image_key TEXT,        -- e.g., "dummy/user_beginner_001_calendar.png"
  
  -- Progression metadata (filled after Haiku Call 2)
  weight_recommendation TEXT,             -- e.g., "Ready to increase to 18kg"
  last_progression_status TEXT,           -- "ready_to_increase" | "hold" | "drop_weight"
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Demo data: Pre-load image URLs per user (for home screen backup plan)
INSERT INTO user_profiles (user_id, experience_level, progression_graph_url, calendar_heatmap_url, progression_graph_image_key, calendar_heatmap_image_key) VALUES
  ('user_001', 'demo', 
   'https://storage.googleapis.com/kinetic-demo/dummy/user_001_progress_ladder.png',
   'https://storage.googleapis.com/kinetic-demo/dummy/user_001_calendar.png',
   'dummy/user_001_progress_ladder.png',
   'dummy/user_001_calendar.png'),
  ('user_002', 'demo',
   'https://storage.googleapis.com/kinetic-demo/dummy/user_002_progress_ladder.png',
   'https://storage.googleapis.com/kinetic-demo/dummy/user_002_calendar.png',
   'dummy/user_002_progress_ladder.png',
   'dummy/user_002_calendar.png'),
  ('user_003', 'demo',
   'https://storage.googleapis.com/kinetic-demo/dummy/user_003_progress_ladder.png',
   'https://storage.googleapis.com/kinetic-demo/dummy/user_003_calendar.png',
   'dummy/user_003_progress_ladder.png',
   'dummy/user_003_calendar.png');
```

### Form Sessions Table
```sql
CREATE TABLE form_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  exercise_id TEXT NOT NULL REFERENCES exercises(id),
  session_date TIMESTAMP,
  weight_value FLOAT,
  weight_unit TEXT,                       -- "kg" | "lb"
  created_at TIMESTAMP DEFAULT NOW()
);

-- Demo data: 1 real session per user (recorded video + pipeline analysis)
INSERT INTO form_sessions (user_id, exercise_id, session_date, weight_value, weight_unit) VALUES
  ('user_001', 'leg_001_goblet', NOW(), 12, 'kg'),
  ('user_002', 'leg_001_goblet', NOW(), 14, 'kg'),
  ('user_003', 'leg_001_goblet', NOW(), 16, 'kg');
```

### Form Analysis Results Table
```sql
CREATE TABLE form_analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES users(id),
  exercise_id TEXT NOT NULL REFERENCES exercises(id),
  session_id UUID NOT NULL REFERENCES form_sessions(id),
  
  -- Input data
  weight_value FLOAT,
  weight_unit TEXT,
  
  -- MediaPipe output (from Squad 3)
  biomechanics_json JSONB,                -- { rep_1: { knee_angle, hip_angle, ..., bottom_frame, bottom_timestamp_ms }, ... }
  quality_gate_status TEXT,               -- "pass" | "fail" (if fail, includes error reason)
  quality_gate_error_code TEXT,           -- e.g., "occlusion_left_side", "poor_angle"
  
  -- OpenCV outputs
  overlay_video_url TEXT,                 -- GCS path to full video with skeleton overlay
  annotated_frame_url TEXT,               -- GCS path to worst-rep annotated image
  
  -- Haiku Call 1 output
  haiku_call_1_output JSONB,              -- { overall_score, per_rep_scores[], posture, stability, movement, range_of_motion, coaching_text, issues[] }
  
  -- Haiku Call 2 output (async)
  haiku_call_2_output JSONB,              -- { vs_previous_delta, posture_delta, stability_delta, movement_delta, range_of_motion_delta, weight_recommendation, progression_status }
  
  -- Status tracking
  status TEXT,                            -- "uploaded" → "processing" → "complete" → "error"
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Gold Standard Biomechanics Table
```sql
CREATE TABLE gold_standard_biomechanics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exercise_id TEXT NOT NULL REFERENCES exercises(id),
  video_url TEXT,                         -- GCS path to reference video
  reference_name TEXT,                    -- e.g., "PT Form Model 1"
  
  -- Reference angles (from good-form videos)
  knee_angle_range JSONB,                 -- { min: 80, max: 95 }
  hip_angle_range JSONB,                  -- { min: 80, max: 95 }
  ankle_dorsiflexion_range JSONB,         -- { min: 25 }
  
  biomechanics_json JSONB,                -- Full biomechanics data from pipeline
  created_at TIMESTAMP DEFAULT NOW()
);

-- Demo data: Insert 3 reference videos
INSERT INTO gold_standard_biomechanics (exercise_id, video_url, reference_name, knee_angle_range, hip_angle_range, ankle_dorsiflexion_range) VALUES
  ('leg_001_goblet', 'gs://kinetic-demo/gold-standard/goblet_ref_1.mp4', 'PT Form Model 1', '{"min": 80, "max": 95}', '{"min": 80, "max": 95}', '{"min": 25}'),
  ('leg_001_goblet', 'gs://kinetic-demo/gold-standard/goblet_ref_2.mp4', 'PT Form Model 2', '{"min": 80, "max": 95}', '{"min": 80, "max": 95}', '{"min": 25}'),
  ('leg_001_goblet', 'gs://kinetic-demo/gold-standard/goblet_ref_3.mp4', 'PT Form Model 3', '{"min": 80, "max": 95}', '{"min": 80, "max": 95}', '{"min": 25}');
```

---

## 6. Supabase Storage Setup (Dummy Images Backup Plan)

### Home Screen Image Storage Strategy

**Folder structure in Supabase Storage (or GCS):**
```
kinetic-demo/
├── dummy/
│   ├── user_beginner_001_progress_ladder.png
│   ├── user_beginner_001_calendar.png
│   ├── user_intermediate_001_progress_ladder.png
│   ├── user_intermediate_001_calendar.png
│   ├── user_advanced_001_progress_ladder.png
│   └── user_advanced_001_calendar.png
└── gold-standard/
    ├── goblet_ref_1.mp4
    ├── goblet_ref_2.mp4
    └── goblet_ref_3.mp4
```

### Creating Dummy Images (Design/Squad 1)

**Graph images needed** (1 per user):
- Weight trend over 5 sessions (line chart)
- Example: Beginner user goes 12kg → 14kg → 14kg → 14kg → 16kg
- Can be PNG, SVG, or generated with matplotlib/plotly

**Calendar images needed** (1 per user):
- Heatmap of May 2026 with session dots on specific dates
- Example: Beginner has 5 sessions (May 6, 10, 17, 20, 23)

**Image specs:**
- Dimensions: 480×280px (fits mobile card)
- Format: PNG (simpler) or SVG (scales better)
- Naming: `user_{profile}_{type}.png` (e.g., `user_beginner_001_progress_ladder.png`)

### Frontend: Load Image Based on User Selection

```typescript
// Simple approach: no fetching, just hardcoded URLs
const getDashboardImages = (userId: string) => {
  const imageMap = {
    'user_beginner_001': {
      progressGraphUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_beginner_001_progress_ladder.png',
      calendarUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_beginner_001_calendar.png'
    },
    'user_intermediate_001': {
      progressGraphUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_intermediate_001_progress_ladder.png',
      calendarUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_intermediate_001_calendar.png'
    },
    'user_advanced_001': {
      progressGraphUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_advanced_001_progress_ladder.png',
      calendarUrl: 'https://storage.googleapis.com/kinetic-demo/dummy/user_advanced_001_calendar.png'
    }
  };
  return imageMap[userId] || imageMap['user_beginner_001'];
};

// On home screen:
const { progressGraphUrl, calendarUrl } = getDashboardImages(selectedUserId);

// Render:
<img src={progressGraphUrl} alt="Progress Ladder" />
<img src={calendarUrl} alt="Calendar" />
```

### Backup if Frontend Logic Not Ready

**If Squad 1 runs out of time building real graph generation:**
1. Create 3 dummy PNG images (progress + calendar for each user)
2. Upload to GCS/Supabase Storage
3. Add `progression_graph_url` + `calendar_heatmap_url` to `user_profiles` table
4. Frontend queries: `GET /api/users/{userId}/dashboard-images`
5. Backend returns: `{ progressGraphUrl, calendarUrl }`
6. Frontend renders images directly (no math, no rendering logic needed)

**This is a 2-hour job instead of 8 hours and requires zero frontend complexity.**

---

## 7. Backend Dev Instructions (Supabase)

### User Creation
- **Do NOT generate UUIDs** for new users
- **Use hardcoded IDs only**: `user_beginner_001`, `user_intermediate_001`, `user_advanced_001`
- When frontend sends profile selection, assign the corresponding hardcoded ID
- Each ID can only be created once; enforce uniqueness at DB level
- Email must be unique and provided by frontend

### Exercise ID Setup
- Create Exercise table with these columns: `id` (TEXT, PRIMARY KEY), `name`, `slug`, `category`, `difficulty`, `description`, `primary_muscles` (ARRAY), `secondary_muscles` (ARRAY), `equipment` (ARRAY), `created_at`
- Add initial exercise record: `leg_001_goblet` (see schema above)
- Future exercises follow pattern: `leg_002_rdl`, `leg_003_*`, etc.

### Session Data Structure
- Form_sessions table: `id` (UUID), `user_id` (TEXT, FK to users), `exercise_id` (TEXT, FK to exercises), `session_date` (TIMESTAMP), `weight_value` (FLOAT), `weight_unit` (TEXT)
- Form_analysis_results table: stores all pipeline outputs (biomechanics JSON, Haiku outputs, image URLs)
- Index on `user_id` + `session_date` for fast session lookup per user
- Pre-populate with 5 sessions per demo user (see demo data in schemas above)

## 7. Immediate Next Steps

- [ ] Backend dev: Set up Supabase schema with hardcoded user IDs (no UUID generation)
- [ ] Backend dev: Create Exercise table with `leg_001_goblet` record
- [ ] Frontend: Implement profile selection → hardcoded ID assignment logic
- [ ] Set up indexes on user_id, exercise_id, and dates for fast queries
- [ ] Define privacy/data retention policies (how long do we keep session data?)
