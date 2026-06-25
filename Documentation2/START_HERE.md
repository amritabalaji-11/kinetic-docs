# 🚀 Kinetic Documentation - Start Here

**Last Updated**: June 24, 2026  
**Purpose**: Understand current state of Kinetic before building anything new

---

## 15-Second Overview

Kinetic is an **AI-powered fitness form analysis platform**. Users upload exercise videos, get **real-time form coaching** (what went wrong), then **progression recommendations** (increase weight or fix form?).

```
User uploads video
    ↓ (500ms)
Quality gate (is video clear enough?)
    ↓ (if pass)
MediaPipe (detect body joints)
    ↓
Haiku Call 1 (analyze form, score 0-100)
    ↓ (immediately to Tab 1)
User sees: "Your form score: 74/100. Work on: chest position"
    ↓ (meanwhile, async in background)
Haiku Call 2 (compare to previous session)
    ↓ (when ready)
User sees Tab 2: "Great progress! Increase to 18kg next time"
```

---

## ⚙️ Before You Start: Tech Requirements

**Make sure you have these versions installed**:

| Category | Required |
|----------|----------|
| **Backend** | Python 3.14+, FastAPI 0.136+ |
| **Frontend** | Node.js 24.14.0 (LTS), npm 11.9.0+ |
| **Database** | SQLite 3.46+ (included with Python) |

→ **[Full Verified Tech Stack](./ARCHITECTURE/SYSTEM_OVERVIEW.md#-technology-stack)** (all dependencies with exact versions verified from codebase)

---

## What's Built vs What's Missing

**✅ FULLY WORKING**:
- User profiles (CRUD)
- Video upload & analysis pipeline
- Form coaching (Haiku Call 1)
- Progression recommendations (Haiku Call 2)

**⚠️ PARTIALLY DONE / HAS GAPS**:
- Exercise mapping (only 3 hardcoded exercises, no master table)
- Workout builder/logger (frontend only, no backend persistence)

**❌ NOT STARTED**:
- Mobile app
- Advanced features (sharing, trends, etc.)

---

## Choose Your Path

### I'm a Backend Developer

**Want to understand the pipeline?**
1. Read: [ARCHITECTURE/SYSTEM_OVERVIEW.md](./ARCHITECTURE/SYSTEM_OVERVIEW.md) (30 min)
2. Then: [MODULES/02_VIDEO_ANALYSIS.md](./MODULES/02_VIDEO_ANALYSIS.md)
3. Then: Check [TECHNICAL_DEEP_DIVES/](./TECHNICAL_DEEP_DIVES/) for your specific module

**Want to see what's missing?**
1. Read: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) (10 min)
2. See: Exercise Mapping & Workout Builder need backend work

**Want to understand AI coaching?**
1. Read: [MODULES/04_HAIKU_CALL_1.md](./MODULES/04_HAIKU_CALL_1.md)
2. Then: [MODULES/05_HAIKU_CALL_2.md](./MODULES/05_HAIKU_CALL_2.md)
3. Deep dive: [TECHNICAL_DEEP_DIVES/HAIKU_CALL_1_SCORING.md](./TECHNICAL_DEEP_DIVES/HAIKU_CALL_1_SCORING.md)

### I'm a Frontend Developer

**Want to understand data flow?**
1. Read: [ARCHITECTURE/SYSTEM_OVERVIEW.md](./ARCHITECTURE/SYSTEM_OVERVIEW.md) (focus on "Data Flow" section)
2. Then: [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) (SSE real-time updates)

**Want to see what needs building?**
1. Read: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
2. See: Workout Builder needs full backend + Exercise Mapping

### I'm a Product Manager

**Want to understand the product?**
1. Read: [ARCHITECTURE/SYSTEM_OVERVIEW.md](./ARCHITECTURE/SYSTEM_OVERVIEW.md) (high-level overview)
2. Then: [ARCHITECTURE/DECISIONS.md](./ARCHITECTURE/DECISIONS.md) (why we built it this way)

**Want to see what's done and what's next?**
1. Read: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
2. Understand: Blockers & dependencies before new work

---

## Full Documentation Map

```
Documentation2/
│
├── 📖 START_HERE.md (you are here)
│
├── 🏗️ ARCHITECTURE/
│   ├── SYSTEM_OVERVIEW.md (complete architecture)
│   └── DECISIONS.md (why we made key choices)
│
├── 🔧 MODULES/
│   ├── 01_USER_PROFILES.md
│   ├── 02_VIDEO_ANALYSIS.md
│   ├── 03_MEDIAPIPE_PROCESSING.md
│   ├── 04_HAIKU_CALL_1.md
│   ├── 05_HAIKU_CALL_2.md
│   ├── 06_WORKOUT_BUILDER_LOGGER.md
│   └── 07_EXERCISE_MAPPING.md
│
├── 📊 TECHNICAL_DEEP_DIVES/
│   ├── QUALITY_GATE_LOGIC.md
│   ├── HAIKU_CALL_1_SCORING.md
│   ├── HAIKU_CALL_2_PROGRESSION.md
│   ├── ID_GENERATION.md
│   ├── DATABASE_SCHEMA.md
│   ├── ASYNC_TIMING.md
│   └── EXERCISE_MAPPING_DESIGN.md
│
├── 🔗 INTEGRATION_GUIDE.md
│
└── 📋 IMPLEMENTATION_STATUS.md
```

---

## Key Concepts (Reference)

| Term | Meaning |
|------|---------|
| **analysis_id** | UUID tracking one video analysis (generated on upload) |
| **session_id** | UUID tracking one workout session (generated per upload) |
| **user_id** | UUID tracking individual user (persisted in browser) |
| **Haiku Call 1** | AI form coaching (synchronous, immediate feedback) |
| **Haiku Call 2** | AI progression recommendations (async, background) |
| **Quality Gate** | Validation: is video clear enough to analyze? |
| **MediaPipe** | ML model that detects body joint positions from video |
| **SSE** | Server-Sent Events (real-time streaming to frontend) |

---

## Quick Links to Original Documentation

The detailed technical documentation has been preserved in `/Kinetic/Documentation/`:
- [KINETIC_VIDEO_ANALYSIS_FEATURE.md](../Documentation/KINETIC_VIDEO_ANALYSIS_FEATURE.md) - Original video pipeline doc
- [QUALITY_GATE_AND_MEDIAPIPE_LOGIC.md](../Documentation/QUALITY_GATE_AND_MEDIAPIPE_LOGIC.md) - Detailed quality gate explanation
- [HAIKU_CALL_1_AND_CALL_2_EXPLAINED.md](../Documentation/HAIKU_CALL_1_AND_CALL_2_EXPLAINED.md) - Detailed AI coaching logic
- [All other docs](../Documentation/) - Full reference library

---

## Next Steps: Getting Oriented

**For your first 30 minutes:**
1. ✅ Read this file (you're doing it!)
2. ⏭️ Read [ARCHITECTURE/SYSTEM_OVERVIEW.md](./ARCHITECTURE/SYSTEM_OVERVIEW.md)
3. ⏭️ Read [MODULE_BREAKDOWN.md](./MODULE_BREAKDOWN.md)

**Then choose based on your role** (see above)

---

## Questions?

- **"Where is [feature] built?"** → Check [MODULE_BREAKDOWN.md](./MODULE_BREAKDOWN.md)
- **"What's missing before I can build X?"** → Check [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
- **"How does X connect to Y?"** → Check [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **"Why did we choose architecture A over B?"** → Check [ARCHITECTURE/DECISIONS.md](./ARCHITECTURE/DECISIONS.md)

---

**Ready?** → [Read ARCHITECTURE/SYSTEM_OVERVIEW.md](./ARCHITECTURE/SYSTEM_OVERVIEW.md)
