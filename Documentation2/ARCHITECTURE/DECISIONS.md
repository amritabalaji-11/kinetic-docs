# Key Architecture Decisions

**Purpose**: Understand *why* the system is built the way it is  
**Read Time**: 15-20 minutes  
**Audience**: All team members (helps understand trade-offs)

---

## Decision 1: Async Pipeline (Not Blocking)

### What We Decided
Video analysis runs **in the background** after upload returns, instead of making user wait 30-60 seconds.

### The Trade-off Matrix

| Aspect | Async (Our Choice) | Sync (Alternative) |
|--------|-------|---------|
| **User Wait Time** | 500ms | 30-60s |
| **UX** | Fast feedback ✅ | Long hang ❌ |
| **Server Concurrency** | Handle 100s of uploads | Only 1 upload at a time |
| **Code Complexity** | More complex ❌ | Simpler ✅ |
| **Error Handling** | Harder (async failures) ❌ | Easier ✅ |
| **Error Messages** | Delayed (SSE) | Immediate |

### Why Async Wins

**Scenario**: 10 users upload videos simultaneously

❌ **With Sync**:
- User 1 uploads → waits 45 seconds
- User 2 uploads → waits 45 seconds (queued)
- User 3-10 → all waiting behind each other
- Server appears frozen

✅ **With Async**:
- User 1 uploads → gets response immediately
- User 2 uploads → gets response immediately
- Server processes all 10 in parallel
- Better UX for everyone

### How We Handle Error Handling

Since analysis happens async, errors don't come back in the response. Instead:
1. Frontend opens SSE stream (Server-Sent Events)
2. Backend emits error event if analysis fails
3. Frontend shows error on loading page
4. User sees "Video too dark - try again"

```
POST /upload → {"analysis_id": "abc-123"} ← user gets response
    ↓
GET /analysis/abc-123/stream ← SSE stream opens
    ↓
Backend: Quality gate FAILS
    ↓
SSE event: {"event": "error", "code": "POOR_QUALITY", "message": "Video too dark..."}
    ↓
Frontend: Display error
```

---

## Decision 2: Two Haiku Calls (Not One)

### What We Decided
Split AI coaching into two separate API calls instead of doing everything in one call.

### The Split

**Call 1 (Synchronous)**:
- Input: Current session only
- Output: Form score, root causes, coaching cues
- Timing: Blocks pipeline (5-10s)
- User sees: Immediately (Tab 1)

**Call 2 (Asynchronous)**:
- Input: Current + previous session
- Output: Weight recommendation, trends
- Timing: Background job (5-10s, doesn't block)
- User sees: Later (Tab 2)

### Why Split Wins

#### Alternative 1: Single Call (Both Features)

```
Call Haiku with:
├─ Current session data
├─ Previous session data (must fetch first)
└─ "Analyze form AND provide progression coaching"

Problems:
├─ Must look up previous session BEFORE calling Haiku
├─ Previous session might not exist (delays Call 1)
├─ Delays form feedback (user has to wait for history lookup)
└─ If first user/exercise → Call still runs but no comparison
```

#### Alternative 2: No Call 1, Only Call 2

```
Pros: Only 1 API call
Cons:
├─ No real-time form feedback
├─ User doesn't know if form was good until next session
├─ Can't iterate within same session
└─ Worse UX
```

### Our Split (Best of Both)

```
Call 1 happens IMMEDIATELY:
├─ No history lookup needed
├─ Form feedback ready in 5-10s
├─ User can see score and fix immediately
└─ Tab 1 unlocks fast

Call 2 happens IN BACKGROUND:
├─ Has time to look up previous session
├─ Compares sessions and applies weight rules
├─ Doesn't block form feedback
└─ Tab 2 unlocks when ready
```

**Result**: User gets immediate form feedback, progression feedback is bonus (arrives ~10s later).

---

## Decision 3: Quality Gate First

### What We Decided
**Before** running expensive MediaPipe processing, validate that the video is clear enough to analyze.

### The Cost Analysis

**MediaPipe is expensive** (20-30 seconds of GPU processing):
```
1 "bad" video = 30 seconds of wasted computation
100 bad videos = 50 minutes of wasted computation
```

**Quality Gate is cheap** (1-2 seconds):
```
1 "bad" video = 2 seconds to detect it's bad + error to user
100 bad videos = ~3 minutes to reject them all
```

### The Decision

```
User uploads video
  ↓
Quality Gate (fast check): Is video clear?
  ├─ If NO (dark/blurry/wrong angle) → Return error in 2 seconds
  │   User sees: "Try again with better lighting"
  │   Saved: 28 seconds of wasted processing
  │   
  └─ If YES → Run MediaPipe (expensive processing)
      User sees: "Analyzing..." progress bar
      Result: Form analysis ready
```

### Why This Order

❌ **Wrong Way**: MediaPipe first, quality gate second
```
Run MediaPipe (30s) → Then check quality
  Problem: Wasted 30s on dark/blurry video
  Wasted: GPU compute, time, cost
```

✅ **Right Way**: Quality gate first, MediaPipe second
```
Check quality (2s) → If pass, run MediaPipe (30s)
  Benefit: Fail fast on bad videos
  Saved: 28s per bad video
```

---

## Decision 4: SSE Streaming (Not Polling)

### What We Decided
Use **Server-Sent Events** to stream progress to frontend, instead of frontend repeatedly asking "Are you done yet?"

### The Comparison

#### Polling (Alternative)

```javascript
// Frontend: "Ask every 500ms if analysis is done"
const checkStatus = setInterval(() => {
  fetch('/analysis/abc-123/status')
    .then(r => r.json())
    .then(data => {
      progressBar.value = data.percentage
      if (data.done) clearInterval(checkStatus)
    })
}, 500)

// Problem:
// 60-second analysis = 120 HTTP requests
// 100 concurrent users = 12,000 requests/minute
// Server hammered with unnecessary requests
```

#### SSE (Our Choice)

```javascript
// Frontend: "Open stream and listen"
const eventSource = new EventSource('/analysis/abc-123/stream')
eventSource.onmessage = (e) => {
  const data = JSON.parse(e.data)
  progressBar.value = data.percentage
}

// Benefit:
// Single persistent connection per user
// 100 concurrent users = 100 connections
// Server pushes updates (no request spam)
```

### Why SSE Wins

| Aspect | Polling | SSE (Our Choice) |
|--------|---------|----------|
| **Connections** | 1000s of requests | 1 persistent connection |
| **Server Load** | High ❌ | Low ✅ |
| **Update Latency** | 250-500ms delay | Instant ✅ |
| **UX** | Jumpy progress bar | Smooth updates ✅ |
| **Mobile Battery** | Drains faster | Better ✅ |

---

## Decision 5: Database Persistence (Not Streaming Directly)

### What We Decided
Store **all results in database**, not send Haiku response directly to frontend.

### The Comparison

#### Direct Streaming (Alternative)

```
Haiku API response → SSE stream to frontend
  ↓
Problems:
├─ If frontend crashes → data lost
├─ If user closes browser → can't view results later
├─ Progression comparison needs to look up previous (requires DB anyway)
└─ Mobile app can't work (needs API endpoint)
```

#### Database Storage (Our Choice)

```
Haiku API response → Store in form_analysis_results table
  ↓
Frontend: GET /analysis/{id} → fetch from database
  ↓
Benefits:
├─ ✅ Data persists (view results anytime)
├─ ✅ Progression can compare (both sessions in DB)
├─ ✅ Multiple clients supported (web, mobile, API)
├─ ✅ Historical tracking (user can see all past analyses)
```

### Timeline

```
[With DB Storage]

T=40s: Haiku Call 1 completes
  ├─ Store in form_analysis_results (INSERT)
  ├─ SSE event: "analysis_ready"
  └─ Frontend fetches from GET /analysis/{id}

T=50s: Haiku Call 2 completes
  ├─ Store in progression_results (INSERT)
  ├─ SSE event: "haiku_call_2_complete"
  └─ Frontend fetches from GET /analysis/{id}/progression

Result:
├─ ✅ Tab 1 shows form feedback (from DB)
├─ ✅ Tab 2 shows progression (from DB)
├─ ✅ User can close app, reopen, still see results
└─ ✅ Admin can query all results for analytics
```

---

## Summary: Why These Decisions

| Decision | Why |
|----------|-----|
| **Async Pipeline** | Faster UX, better concurrency, handle scale |
| **Two Haiku Calls** | Immediate form feedback, async progression, best UX |
| **Quality Gate First** | Fail fast, save expensive compute on bad videos |
| **SSE Streaming** | Real-time UX, low server load, better UX than polling |
| **DB Persistence** | Supports reusability, progression comparison, history, mobile |

---

## What Didn't Make the Cut

### We Considered But Rejected:

**Caching Haiku responses by exercise**
- Idea: Cache coaching output for "goblet squat with 20kg"
- Problem: Every user is different (form varies greatly)
- Decision: Always call Haiku (no caching)

**Running MediaPipe on GPU-enabled instances**
- Idea: Faster processing (MediaPipe supports GPU)
- Problem: Cost, infrastructure complexity
- Decision: CPU-only for now (30s is acceptable)

**Storing frame-by-frame data**
- Idea: Store all 100+ frames of analysis data
- Problem: Database bloat, storage cost
- Decision: Store aggregates only (mean angles, rep counts)

---

## Next Time You Wonder "Why Did We..."

This document explains the big architectural decisions. For implementation details, see:
- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - How it all fits together
- [../IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) - What's built, what's not
- [../MODULE_BREAKDOWN.md](../MODULE_BREAKDOWN.md) - Who owns what

