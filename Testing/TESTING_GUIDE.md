# Squat Analysis — Model A/B Test Guide
**Project:** Kinetic AIPM-1  
**For:** Engineering & Coaching Team  
**Last updated:** May 2026  

---

## Developer Handoff — What to do

This section is for the developer running the test. Everything you need is below.

### Step 1 — Folder structure

All files go inside the `Testing/` folder. Create two subfolders if they don't exist:

```
Testing/
  run_test.py              ← the test script (already here)
  TESTING_GUIDE.md         ← this file
  videos/                  ← PUT THE 6 VIDEOS HERE
    v1_depth_fault.mp4
    v2_depth_good.mp4
    v3_knee_fault.mp4
    v4_knee_good.mp4
    v5_torso_fault.mp4
    v6_torso_good.mp4
  json/                    ← PUT YOUR MEDIAPIPE OUTPUT HERE (one file per video)
    v1.json
    v2.json
    v3.json
    v4.json
    v5.json
    v6.json
  results/                 ← created automatically when the script runs
    scores.csv
    feedback_for_rating.md
    raw_outputs.json
```

**File naming is exact — the script will skip any file it can't find by name.**

---

### Step 2 — Run MediaPipe on each video

Run your MediaPipe extraction script on each of the 6 videos. Save the output as `.json` with the filenames above (`v1.json` through `v6.json`) in the `json/` folder.

Each JSON file should be the raw MediaPipe output for that video — an array of frame objects with joint angles per frame. If your script outputs a different schema, update `JSON_FILES` at the top of `run_test.py`.

---

### Step 3 — Set API keys

```bash
export NVIDIA_API_KEY=<key provided by PM>
export GOOGLE_API_KEY=<key provided by PM>
```

Confirm they're set:
```bash
echo $NVIDIA_API_KEY
echo $GOOGLE_API_KEY
```

> Keys only last for the current terminal session. If you close Terminal, re-run the export commands before running the script.

---

### Step 4 — Run the test

```bash
cd /path/to/Testing
python run_test.py
```

Runs all three variants sequentially. Expected time:
- Control: ~2–4 min
- Variant A: ~5–10 min
- Variant B: ~8–15 min (video upload + processing)

Live output:
```
──────────────────────────────────────────
  Control  (meta/llama-3.1-70b-instruct)
──────────────────────────────────────────
  V1 ... ✅  1240 ms
  V2 ... ✅  1180 ms
  V3 ... ❌  1310 ms
  ...
```

---

### Step 5 — Send back these 3 files

Once the script finishes, send the PM all three files from the `results/` folder:

| File | What it contains |
|---|---|
| `results/scores.csv` | Form accuracy per video per variant — auto-filled. Four coaching quality columns left blank for human rating. |
| `results/feedback_for_rating.md` | Coaching text from all variants, grouped by video. Variant labels hidden inside comments — used for blind coaching quality rating. |
| `results/raw_outputs.json` | Full model responses for debugging. Check the `evidence` field when a model gets something wrong. |

---

## PT / Coaching Feedback — Not a blocker

The personal trainer's feedback is used **after** the test runs, not before. It is not needed to execute the script.

**What the PT does:**
1. Receives `results/feedback_for_rating.md` after the test runs
2. Reads each coaching response without knowing which model wrote it (variant labels are hidden)
3. Rates each response 1–5 per parameter (Posture / Stability / Movement Quality / Range of Motion)
4. Returns ratings to be added to `scores.csv`

**Sequence:**
```
Developer runs test → produces results files
                    ↓
PM sends feedback_for_rating.md to PT
                    ↓
PT rates coaching quality blind (24–48 hrs)
                    ↓
PM adds PT ratings to scores.csv → makes architecture decision
```

The test can run as soon as MediaPipe JSON is ready. PT rating is a parallel step after execution.

---

## What we're testing

Three model variants on 6 standardised Goblet Squat videos:

| | Variant | Input | Model |
|---|---|---|---|
| **Control** | JSON only | MediaPipe joint angles (no video) | Llama 3.1 70B (NVIDIA NIM) |
| **Variant A** | JSON + frames | Joint angles + 32 sampled video frames | Llama 3.2 90B Vision (NVIDIA NIM) |
| **Variant B** | JSON + video | Joint angles + full video file | Gemini 2.0 Flash (Google AI) |

**What we measure (in priority order):**
1. **Form accuracy** — does the model correctly detect the fault in each video?
2. **Latency** — how long does each API call take?
3. **Coaching quality** — how good is the text feedback? *(PT-rated after test runs)*

**Four feedback parameters per analysis:**
- Posture, Stability, Movement Quality, Range of Motion
- Each has: what the user is doing well / critical observations / one recommendation

---

## Output files

### `results/scores.csv`
Auto-filled: Video, Variant, Model, Fault Tested, Ground Truth, Model Output, Correct ✅/❌, Confidence, Latency (ms).

Four columns left blank for PT to fill in after reading `feedback_for_rating.md`:
- Posture /5
- Stability /5
- Movement Quality /5
- Range of Motion /5

### `results/feedback_for_rating.md`
Coaching feedback from all variants, grouped by video. **Variant labels are hidden inside HTML comments** — rate without looking at them.

### `results/raw_outputs.json`
Full model responses for debugging. Check `evidence` field when `correct = ❌` to see the model's reasoning.

---

## PT rating instructions

**Who should rate:** Someone with coaching or biomechanics knowledge. Ideally not the person who ran the test.

**How to rate:**
1. Open `results/feedback_for_rating.md`
2. Read each entry top to bottom — **do not look at `<!-- Variant: ... -->` comments** until all ratings are complete
3. For each parameter (Posture / Stability / Movement Quality / Range of Motion), assign 1–5:

| Score | Criteria |
|---|---|
| **5** | Specific and accurate. Recommendation is one cue that directly addresses the observed fault |
| **4** | Accurate but slightly generic. Correct issue identified, cue could be more specific |
| **3** | Partially correct. Real issue mentioned but main fault missed or misidentified |
| **2** | Inaccurate. Wrong fault identified, or contradicts the video data |
| **1** | Missing. Field is null or empty when a fault was clearly present |

4. Add ratings to blank columns in `results/scores.csv`

**Important:** If a video shows no fault (V2, V4, V6) and `critical_observations = null`, that is **correct behaviour** — do not penalise it. A model that invents problems on good-form videos is a false positive.

---

## Interpreting results

### Form accuracy
Each variant is scored out of 6 (one correct/incorrect per video).
- Score ≤ 3/6 → variant is disqualified
- Check V3/V4 (knee tracking) specifically — this is the fault that visual input should help most with

### Latency
- < 3s: acceptable for post-session review
- 3–8s: borderline
- > 8s: too slow for in-session use

### Confidence calibration
If the model returns confidence ≥ 0.8 on an incorrect prediction, flag it — high-confidence wrong answers are dangerous in a coaching product.

### Picking a winner
1. Eliminate any variant scoring ≤ 3/6 on form accuracy
2. If form accuracy is tied, prefer lower latency
3. If latency is also tied, coaching quality breaks the tie
4. Document cost per video for the winning variant (needed for product pricing)

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `NVIDIA_API_KEY not set` | Env var missing | `export NVIDIA_API_KEY=...` |
| 404 on `llama-3.2-90b-vision` | Model not on your account | Log into build.nvidia.com, confirm the model slug |
| Gemini upload times out | Large video file | Trim to ≤ 30s or reduce to 720p |
| JSON parse error | Model returned prose not JSON | Check `raw_outputs.json` — re-run that single video |
| `videos/v1_depth_fault.mp4 not found` | Wrong filename | Rename to match exactly what's in `VIDEO_FILES` at top of `run_test.py` |
| All variants score 6/6 | Faults too obvious | Re-test with subtler fault videos after pipeline is validated |

---

## What's not automated

- **Coaching quality ratings** — PT rates these after the test runs (not a blocker)
- **Key-moment frame sampling** — `run_test.py` currently uses uniform frame sampling for Variant A. The `extract_key_frames()` function is stubbed — can be upgraded to sample at peak depth and top-of-squat using MediaPipe knee angle peaks

---

*Questions: contact the ML lead or open an issue in the repo.*
