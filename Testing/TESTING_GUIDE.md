# Squat Analysis — Model A/B Test Guide
**Project:** Kinetic AIPM-1  
**For:** Engineering & Coaching Team  
**Last updated:** May 2026  

---

## Developer Handoff — Step by Step

---

### Step 1 — Install dependencies

```bash
pip install openai google-generativeai opencv-python
```

Python 3.9+ required. Run this once — no need to repeat.

---

### Step 2 — Place all files in the correct folders

All files go inside the `Testing/` folder. The structure must be exactly:

```
Testing/
│
├── run_test.py                          ← already here
├── TESTING_GUIDE.md                     ← this file
│
├── videos/                              ← 6 original .mp4 recordings
│     v1_depth_fault.mp4
│     v2_depth_good.mp4
│     v3_knee_fault.mp4
│     v4_knee_good.mp4
│     v5_torso_fault.mp4
│     v6_torso_good.mp4
│
├── processed_videos/                    ← 6 MediaPipe-processed videos (10fps, skeleton overlay)
│     v1_depth_fault_processed.mp4
│     v2_depth_good_processed.mp4
│     v3_knee_fault_processed.mp4
│     v4_knee_good_processed.mp4
│     v5_torso_fault_processed.mp4
│     v6_torso_good_processed.mp4
│
├── json/                                ← 6 MediaPipe JSON files (one per video)
│     v1.json
│     v2.json
│     v3.json
│     v4.json
│     v5.json
│     v6.json
│
└── results/                             ← created automatically when the script runs
      scores.csv
      feedback_for_rating.md
      raw_outputs.json
```

**Video → fault mapping:**

| File prefix | Fault | Condition | Camera |
|---|---|---|---|
| v1 | Depth | FAULT | Side |
| v2 | Depth | GOOD | Side |
| v3 | Knee tracking | FAULT | Front |
| v4 | Knee tracking | GOOD | Front |
| v5 | Torso lean | FAULT | Side |
| v6 | Torso lean | GOOD | Side |

Each video has exactly 3 files: one in `videos/`, one in `processed_videos/`, one in `json/`. **File naming is exact — the script will skip any file it can't find by name.**

---

### Step 3 — Set API keys

In your terminal, run all three export commands:

```bash
export NVIDIA_API_KEY_70B=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
export NVIDIA_API_KEY_90B=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
export GOOGLE_API_KEY=AIzaSyC-F-OJASGgg_hAxJ2HIIoobKPN_mhPa20
export OPENAI_API_KEY=<your_openai_key>
export ANTHROPIC_API_KEY=<your_anthropic_key>
```

Confirm all five are set:
```bash
echo $NVIDIA_API_KEY_70B
echo $NVIDIA_API_KEY_90B
echo $GOOGLE_API_KEY
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

Each should print a partial key value. If any prints blank, re-run that export line.

> Keys only last for the current terminal session. If you close Terminal and reopen it, re-run the three export commands before running the script.

> **Security:** Do not commit this file to GitHub with these keys in it.

---

### Step 4 — Smoke test (run this before the full test)

Verify both API connections are working with a quick test before committing to the full 30–55 min run:

```bash
python3 -c "
import os
from openai import OpenAI
import google.generativeai as genai

# Test NVIDIA 70B
client = OpenAI(api_key=os.getenv('NVIDIA_API_KEY_70B'), base_url='https://integrate.api.nvidia.com/v1')
r = client.chat.completions.create(model='meta/llama-3.1-70b-instruct', messages=[{'role':'user','content':'say ok'}], max_tokens=5)
print('NVIDIA 70B:', r.choices[0].message.content.strip())

# Test NVIDIA 90B
client2 = OpenAI(api_key=os.getenv('NVIDIA_API_KEY_90B'), base_url='https://integrate.api.nvidia.com/v1')
r2 = client2.chat.completions.create(model='nvidia/llama-3.2-90b-vision-instruct', messages=[{'role':'user','content':'say ok'}], max_tokens=5)
print('NVIDIA 90B:', r2.choices[0].message.content.strip())

# Test Google
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
r3 = genai.GenerativeModel('gemini-2.0-flash').generate_content('say ok')
print('Google Gemini:', r3.text.strip())
"
```

Expected output — all three lines should print something (not an error):
```
NVIDIA 70B: ok
NVIDIA 90B: ok
Google Gemini: ok
```

If any line throws an error, fix that connection before running the full test.

---

### Step 5 — Run the test

```bash
cd /path/to/Testing
python run_test.py
```

Runs all five variants sequentially. Expected total time: **30–55 minutes.**

| Variant | Expected time |
|---|---|
| Control | ~2–4 min |
| Variant A | ~5–10 min |
| Variant B | ~8–15 min |
| Variant D | ~8–15 min |
| Variant E | ~5–10 min |

Live output looks like this:
```
──────────────────────────────────────────────────
  Control  (meta/llama-3.1-70b-instruct)
──────────────────────────────────────────────────
  V1 ... ✅  1240 ms
  V2 ... ✅  1180 ms
  V3 ... ❌  1310 ms
  V4 ... ✅  980 ms
  V5 ... ✅  1420 ms
  V6 ... ✅  1100 ms
```

✅ = model got the fault detection correct. ❌ = wrong detection (not a crash — the test continues).

---

### Step 6 — Verify the run completed correctly

Once the script finishes, check the following before sending results to the PM:

**1. All 5 variants ran — no SKIP lines**
If you see `SKIP — processed_videos/ folder not found`, Variants D and E were skipped. Add the processed videos and re-run.

**2. Results folder has exactly 3 files**
```bash
ls results/
```
Should show: `scores.csv`, `feedback_for_rating.md`, `raw_outputs.json`

**3. scores.csv has 30 rows (5 variants × 6 videos)**
```bash
wc -l results/scores.csv
```
Should print `31` (30 data rows + 1 header).

**4. No ERROR entries**
```bash
grep ERROR results/scores.csv
```
Should return nothing. If errors appear, check `raw_outputs.json` for the model's raw response on that video — most errors are either a JSON parse failure (model returned prose) or a video upload timeout.

**5. raw_outputs.json is valid JSON**
```bash
python3 -c "import json; json.load(open('results/raw_outputs.json')); print('valid')"
```
Should print `valid`.

---

### Step 7 — Send these 3 files to the PM

| File | What it contains |
|---|---|
| `results/scores.csv` | Form accuracy per video per variant — auto-filled. Four coaching quality columns left blank for human rating. |
| `results/feedback_for_rating.md` | Coaching text from all variants, grouped by video. Variant labels hidden — used for blind coaching quality rating. |
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

Five variants on 6 standardised Goblet Squat videos:

| | Variant | Input | Model |
|---|---|---|---|
| **Control** | JSON only | MediaPipe joint angles (no video) | Llama 3.1 70B (NVIDIA NIM) |
| **Variant A** | JSON + frames | Joint angles + 32 sampled frames (original video) | Llama 3.2 90B Vision (NVIDIA NIM) |
| **Variant B** | JSON + original video | Joint angles + full original video | Gemini 2.0 Flash (Google AI) |
| **Variant D** | JSON + processed video | Joint angles + 10fps skeleton-overlay video | Gemini 2.0 Flash (Google AI) |
| **Variant E** | JSON + processed video | Joint angles + 10fps skeleton-overlay video | Llama 3.2 90B Vision (NVIDIA NIM) |

**Why D and E together:**

| | Original video | Processed video (10fps, skeleton overlay) |
|---|---|---|
| **Gemini 2.0 Flash** | Variant B | Variant D |
| **Llama 3.2 90B Vision** | Variant A (frames) | Variant E |

This lets you answer two questions from one test run: *does the skeleton overlay improve accuracy?* (B vs D, A vs E) and *which model handles annotated video better?* (D vs E).

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
| `processed_videos/v1_depth_fault_processed.mp4 not found` | Processed video missing | Re-run MediaPipe extraction — check that your script saves the overlay video to `processed_videos/` |
| All variants score 6/6 | Faults too obvious | Re-test with subtler fault videos after pipeline is validated |

---

## What's not automated

- **Coaching quality ratings** — PT rates these after the test runs (not a blocker)
- **Key-moment frame sampling** — `run_test.py` currently uses uniform frame sampling for Variant A. The `extract_key_frames()` function is stubbed — can be upgraded to sample at peak depth and top-of-squat using MediaPipe knee angle peaks

---

*Questions: contact the ML lead or open an issue in the repo.*
