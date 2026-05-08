# Kinetic — Frontend Response Schemas
**Task:** S1-W5-03  
**Date:** May 9, 2026  
**Scope:** Form analysis result · Form comparison · Auth · User profile  
**Excludes:** SSE events (defined separately in S1-W5-06a)

---

## 1. Form Analysis Result
**Endpoint:** `GET /analysis/{id}/result`  
**When:** User is navigated to Results screen after `analysis_complete` SSE fires

```json
{
  "analysis_id": "uuid",
  "exercise": "Goblet Squat",
  "weight_kg": 20,
  "rep_count": 10,
  "created_at": "2026-05-09T10:32:00Z",
  "quality_gate_status": "GOOD",

  "overall_score": 72,

  "verdict": [
    "Your depth is consistent — all 10 reps reached full depth.",
    "Descent is too fast across every rep — you are dropping rather than controlling the movement.",
    "Form holds well until rep 7 where fatigue starts showing in back angle and pace."
  ],

  "parameters": {
    "posture": {
      "score": 68,
      "affirmation": "Back angle stays consistent across most reps.",
      "observation": "Back angle peaked at 38° on rep 5 — above your 34° average.",
      "tips": ["Brace your core before each descent", "Keep chest tall as you approach depth"]
    },
    "stability": {
      "score": 80,
      "affirmation": "No heel lift detected — good ankle mobility.",
      "observation": "Slight knee cave on early ascent in reps 5–10.",
      "tips": ["Drive knees outward as you begin to rise"]
    },
    "movement_quality": {
      "score": 85,
      "affirmation": "All 10 reps reached full depth consistently.",
      "observation": "Ankle dorsiflexion reducing in later reps.",
      "tips": ["Try elevating heels slightly if ankle tightness limits depth"]
    },
    "tempo": {
      "score": 55,
      "affirmation": "Pause at bottom is consistent — averaging 0.95s.",
      "observation": "Descent is very fast (0.07–0.17s) — dropping rather than controlling.",
      "tips": ["Aim for at least 1.5s lowering", "Think: slow lower, fast push"]
    }
  },

  "reps": [
    { "rep": 1,  "score": 78, "verdict": "Strong opening rep — good depth and consistent back angle." },
    { "rep": 2,  "score": 77, "verdict": "Solid. Slight speed on descent but well controlled overall." },
    { "rep": 3,  "score": 76, "verdict": "Consistent. Minor forward lean beginning." },
    { "rep": 4,  "score": 75, "verdict": "Holding up well — tempo consistent." },
    { "rep": 5,  "score": 70, "verdict": "Back angle spike to 38° — first sign of fatigue." },
    { "rep": 6,  "score": 72, "verdict": "Recovery rep — back angle returns to average." },
    { "rep": 7,  "score": 69, "verdict": "Fatigue showing — slower concentric and increased lean." },
    { "rep": 8,  "score": 68, "verdict": "Continued fatigue. Consider stopping here next time." },
    { "rep": 9,  "score": 65, "verdict": "Significant fatigue. Depth maintained but form degrading." },
    { "rep": 10, "score": 63, "verdict": "Fatigue fully visible — slower pace and forward lean." }
  ],

  "annotated_frames": [
    {
      "label": "worst_rep_bottom",
      "url": "https://storage.googleapis.com/kinetic-videos/analyses/{analysis_id}/frame_bottom.jpg"
    },
    {
      "label": "worst_rep_top",
      "url": "https://storage.googleapis.com/kinetic-videos/analyses/{analysis_id}/frame_top.jpg"
    }
  ]
}
```

**Notes:**
- `worst_rep` = rep with lowest overall score
- `annotated_frames` = 2 frames (bottom + top) of the worst rep with green/red joint overlays
- `quality_gate_status` surfaced so frontend can show soft confidence warning if ACCEPTABLE

---

## 2. Form Comparison
**Endpoint:** `GET /analysis/{id}/comparison`  
**When:** User taps the Form Comparison toggle on Results screen  
**Pre-generated:** Yes — generated async after `analysis_complete` fires, not on toggle tap  
**Logic:** Current session vs latest previous session for same exercise_id + user_id

### 2a. Has previous session
```json
{
  "has_comparison": true,
  "empty_state_message": null,

  "verdict": "Your form has improved 7 points since your last session at 15kg — strong progress as you move to 20kg.",

  "current": {
    "analysis_id": "uuid",
    "date": "2026-05-09",
    "exercise": "Goblet Squat",
    "weight_kg": 20,
    "overall_score": 72,
    "annotated_frame_url": "https://storage.googleapis.com/.../current_frame_bottom.jpg",
    "rep_scores": [78, 77, 76, 75, 70, 72, 69, 68, 65, 63],
    "parameters": {
      "posture": 68,
      "stability": 80,
      "movement_quality": 85,
      "tempo": 55
    }
  },

  "previous": {
    "analysis_id": "uuid",
    "date": "2026-04-25",
    "exercise": "Goblet Squat",
    "weight_kg": 15,
    "overall_score": 65,
    "annotated_frame_url": "https://storage.googleapis.com/.../previous_frame_bottom.jpg",
    "rep_scores": [70, 68, 72, 69, 65, 64, 61],
    "parameters": {
      "posture": 60,
      "stability": 75,
      "movement_quality": 80,
      "tempo": 48
    }
  },

  "variance": {
    "overall_score": 7,
    "parameters": {
      "posture": 8,
      "stability": 5,
      "movement_quality": 5,
      "tempo": 7
    }
  },

  "parameter_tips": {
    "posture": "Your back angle is more controlled at 20kg — keep bracing before each descent.",
    "stability": "Knee stability has improved but watch for cave on the ascent as weight increases.",
    "movement_quality": "Depth is consistent at heavier weight — ankle mobility holding well.",
    "tempo": "Still dropping on the descent — controlling this will be critical at your next weight."
  }
}
```

### 2b. No previous session
```json
{
  "has_comparison": false,
  "empty_state_message": "You haven't done a previous Goblet Squat analysis yet. Upload another session to unlock comparison.",
  "verdict": null,
  "current": null,
  "previous": null,
  "variance": null,
  "parameter_tips": null
}
```

**Frontend rendering notes:**
- Variance positive → green · Variance negative → orange
- `rep_scores` arrays plotted at natural length — no padding if rep counts differ
- `annotated_frame_url` per session = worst-rep bottom frame (1 per analysis, for demo)

**Backend async generation plan:**
```
After analysis_complete SSE fires (non-blocking):
  1. Query DB: latest previous session for same exercise_id + user_id
  2a. If found → call Claude with both sessions → store comparison result
  2b. If not found → store has_comparison: false immediately
  Frontend toggle → instant fetch (already stored)
  Edge case: toggle tapped < 5s after results → show brief loading state
```

---

## 3. Auth Responses

### POST /auth/signup and POST /auth/login
Both return the same shape. Auth handled by Supabase (Google OAuth flow).
```json
{
  "token": "jwt-string",
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "display_name": "Amrita"
  }
}
```

**Error (OAuth failure):**
```json
{
  "error": "auth_failed",
  "message": "Google sign-in was cancelled or failed. Please try again."
}
```

---

## 4. User Profile

### GET /users/profile
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "display_name": "Amrita",
  "training_frequency": "3x per week",
  "exercise_preferences": ["goblet_squat"],
  "injury_profile": {
    "areas": ["left_knee"],
    "classification": "recurring",
    "notes": "optional free text"
  }
}
```

### POST /users/profile (update)
Request body — same shape as GET response (partial updates allowed).  
Returns updated profile object on success.

**First-time user (no profile saved yet):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "display_name": "Amrita",
  "training_frequency": null,
  "exercise_preferences": [],
  "injury_profile": null
}
```

---

## 5. DB Change Required

**`form_analyses` table — add 1 field:**

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `annotated_frame_url` | string (nullable) | Squad 2 — written after OpenCV frame extraction | GCS URL of worst-rep bottom frame. NULL until frame extraction completes. |

---

## Changelog
- May 9, 2026: Initial definition — form analysis result, form comparison (async pre-generated), auth, user profile
