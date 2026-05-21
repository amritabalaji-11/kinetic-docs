# Kinetic — Biomechanics Script Specification
**Task:** S3-W5-07  
**Owner:** Squad 3  
**Date:** May 8, 2026  
**Consumes:** Frame payload from S3-W5-06 (selected frames with world/screen landmarks)  
**Outputs:** `Kinetic_Biomechanics_Output_Schema.json` — per-rep + consolidated JSON passed to ~~Nemotron~~ → **Haiku 4.5**

---

## What This Script Does

Takes an array of quality-gated frames from S3-W5-06. Each frame has world landmark coordinates (3D metric), screen landmark coordinates (normalised 0–1), frame_reliability, rep_index, and position_tag.

Computes joint angles, stability metrics, tempo, and error flags for each rep. Aggregates into a consolidated summary with cross-rep trends. Outputs a single JSON for the LLM stage.

---

## Coordinate Systems

| System | Source | Use |
|--------|--------|-----|
| `world_landmarks` | `pose_world_landmarks` | All angle calculations — metric 3D coords, origin at hip |
| `screen_landmarks` | `pose_landmarks` | Knee valgus + foot turn-out only — lateral measurements in camera plane |

---

## Landmark IDs

| ID | Landmark | Used for |
|----|----------|----------|
| 11, 12 | Left/Right Shoulder | Back angle, hip angle, butt wink |
| 23, 24 | Left/Right Hip | Hip angle, back angle, butt wink, rep segmentation |
| 25, 26 | Left/Right Knee | Knee angle, knee valgus |
| 27, 28 | Left/Right Ankle | Knee angle, ankle dorsiflexion |
| 29, 30 | Left/Right Heel | Heel lift detection |
| 31, 32 | Left/Right Foot Index | Ankle dorsiflexion, foot turn-out |

> Nose, elbow, and eye landmarks are **not used** in biomechanics output.

---

## Core Angle Functions

All use world coordinates. Average left + right side unless noted.

```python
import numpy as np

def angle_between(a, b, c):
    """Angle at point b in the triangle a-b-c."""
    v1 = np.array([a.x - b.x, a.y - b.y, a.z - b.z])
    v2 = np.array([c.x - b.x, c.y - b.y, c.z - b.z])
    cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))

# Hip angle: shoulder → hip → knee
hip_angle = (angle_between(lm[11], lm[23], lm[25]) +
             angle_between(lm[12], lm[24], lm[26])) / 2

# Knee angle: hip → knee → ankle
knee_angle = (angle_between(lm[23], lm[25], lm[27]) +
              angle_between(lm[24], lm[26], lm[28])) / 2

# Back angle: torso lean from vertical
def back_angle(shoulder, hip):
    torso = np.array([shoulder.x - hip.x, shoulder.y - hip.y, shoulder.z - hip.z])
    vertical = np.array([0, -1, 0])
    return np.degrees(np.arccos(np.clip(
        np.dot(torso, vertical) / np.linalg.norm(torso), -1.0, 1.0)))
back = (back_angle(lm[11], lm[23]) + back_angle(lm[12], lm[24])) / 2

# Ankle dorsiflexion: knee → ankle → foot_index
dorsiflexion = (angle_between(lm[25], lm[27], lm[31]) +
                angle_between(lm[26], lm[28], lm[32])) / 2
```

---

## Tempo — State Machine

Uses hip angle and `timestamp_ms` to time each phase.

```python
import statistics

class TempoTracker:
    THRESHOLDS = {'descending': 100, 'bottom': 90, 'standing': 160}

    def update(self, hip_angle, timestamp_ms):
        if self.state == 'STANDING' and hip_angle < 100:
            self.state = 'DESCENDING'; self.t = timestamp_ms
        elif self.state == 'DESCENDING' and hip_angle < 90:
            self.eccentric = (timestamp_ms - self.t) / 1000
            self.state = 'BOTTOM'; self.t = timestamp_ms
        elif self.state == 'BOTTOM' and hip_angle > 100:
            self.pause = (timestamp_ms - self.t) / 1000
            self.state = 'ASCENDING'; self.t = timestamp_ms
        elif self.state == 'ASCENDING' and hip_angle > 160:
            self.concentric = (timestamp_ms - self.t) / 1000
            self.total = self.eccentric + self.pause + self.concentric
            self.state = 'STANDING'
            return self._build_output()
```

**Output fields per rep:**

| Field | Computation | Target |
|-------|------------|--------|
| `eccentric` | ms(STANDING→BOTTOM) ÷ 1000 | ≥ 1.5s controlled · < 0.5s = dropped |
| `pause` | ms(BOTTOM phase) ÷ 1000 | 0.5–1.5s ideal |
| `concentric` | ms(BOTTOM→STANDING) ÷ 1000 | ≥ 1.0s controlled |
| `total` | eccentric + pause + concentric | Trend rising = fatigue |
| `tempo_notation` | "0" if < 0.5s else "1" per phase, format "e-p-c" | e.g. "0-1-0" |
| `squat_type` | from knee_angle_min: DEEP/PARALLEL/SHALLOW | DEEP |

---

## Posture — Back Angle + Butt Wink

```python
# Back angle status thresholds
def back_status(angle):
    if angle < 30:  return 'GOOD'
    if angle < 45:  return 'ACCEPTABLE'
    return 'WARNING'

# Butt wink — posterior pelvic tilt at bottom (run AFTER biomechanics)
def butt_wink(shoulder, hip, knee, baseline_angle):
    torso_vec  = np.array([hip.x - shoulder.x, hip.y - shoulder.y, hip.z - shoulder.z])
    pelvis_vec = np.array([knee.x - hip.x, knee.y - hip.y, knee.z - hip.z])
    angle = np.degrees(np.arccos(np.clip(
        np.dot(torso_vec, pelvis_vec) /
        (np.linalg.norm(torso_vec) * np.linalg.norm(pelvis_vec)), -1.0, 1.0)))
    deviation = angle - baseline_angle
    return deviation > 15, round(deviation, 2)  # (detected: bool, severity_deg: float)
```

**Output fields per rep:**

| Field | Computation | Target |
|-------|------------|--------|
| `back_angle_start` | back_angle at position_tag="top" frame | 10–20° |
| `back_angle_max` | max(back_angle) across all frames in rep | < 30° GOOD · 30–45° ACCEPTABLE · > 45° WARNING |
| `back_angle_at_bottom` | back_angle at position_tag="bottom" frame | Lean under max load |
| `time_warning` | Σ frame_duration where back_angle > 30° | Lower = better |
| `time_excessive` | Σ frame_duration where back_angle > 45° | 0.0 ideal |
| `status` | GOOD / ACCEPTABLE / WARNING from back_angle_max | GOOD |
| `butt_wink_detected` | torso–pelvis deviation > 15° vs standing baseline | false |
| `butt_wink_severity_deg` | max deviation in ±10 frames around bottom | < 15° |

---

## Movement Quality — Depth, Hip, Ankle, Foot Turn-out

```python
# Depth classification from knee angle at bottom
def depth_class(knee_angle_min):
    if knee_angle_min < 90:  return 'DEEP'
    if knee_angle_min < 100: return 'PARALLEL'
    return 'SHALLOW'

# Foot turn-out — uses SCREEN coords
def foot_turnout(heel, foot_index):  # screen landmarks (x, y only)
    foot_vec = np.array([foot_index.x - heel.x, foot_index.y - heel.y])
    return np.degrees(np.arctan2(foot_vec[0], -foot_vec[1]))
```

**Output fields per rep:**

| Field | Computation | Target |
|-------|------------|--------|
| `hip_angle_start` | hip_angle at top frame | 160–180° |
| `hip_angle_at_bottom` | hip_angle at bottom frame | 60–90° deep · 90–100° parallel |
| `hip_angle_min` | min(hip_angle) across all frames | < 90° |
| `knee_angle_start` | knee_angle at top frame | 170–180° |
| `knee_angle_at_bottom` | knee_angle at bottom frame | < 90° deep · 90–100° parallel · > 100° shallow |
| `knee_angle_min` | min(knee_angle) across all frames | < 90° |
| `depth_classification` | DEEP / PARALLEL / SHALLOW from knee_angle_min | DEEP |
| `depth_insufficient_flag` | boolean: knee_angle_at_bottom > 100° | false |
| `dorsiflexion_at_bottom` | ankle_dorsiflexion at bottom frame (avg L+R) | > 25° adequate · < 20° restricted |
| `foot_turnout_left` | foot_turnout(left_heel, left_foot_index) at top frame | 10–30° outward |
| `foot_turnout_right` | foot_turnout(right_heel, right_foot_index) at top frame | 10–30° outward |

---

## Stability — Knee Valgus + Heel Lift

```python
# Knee valgus — SCREEN coords — lateral collapse in camera plane
# Run in first 20% of concentric phase (highest risk window)
def knee_valgus_distance(left_knee, right_knee):  # screen x only
    return abs(left_knee.x - right_knee.x)  # smaller = more cave

# Find worst cave in concentric window
concentric_start = first frame after bottom where hip_y starts decreasing
window_end = concentric_start + 0.20 * (top_frame - bottom_frame)
valgus_frames = frames[concentric_start : window_end]
min_dist = min(knee_valgus_distance(f.left_knee, f.right_knee) for f in valgus_frames)
valgus_idx_pct = (frame_of_min - concentric_start) / (window_end - concentric_start)
valgus_phase = 'EARLY' if valgus_idx_pct < 0.33 else 'MID' if < 0.66 else 'LATE'

# Heel lift — world coords
baseline_heel_y = avg(heel.world.y) at top frame  # standing reference
max_heel_y = max(heel.world.y across all rep frames)
heel_lift_detected = (max_heel_y - baseline_heel_y) > 0.02  # 2cm threshold
heel_lift_magnitude = round(max_heel_y - baseline_heel_y, 3)
```

**Output fields per rep:**

| Field | Computation | Target |
|-------|------------|--------|
| `knee_valgus_distance` | min inter-knee x-distance in first 20% concentric | Higher = more stable |
| `valgus_phase` | EARLY < 33% · MID 33–66% · LATE > 66% of concentric | EARLY = highest injury risk |
| `valgus_flag` | boolean: knee_valgus below threshold | false |
| `heel_lift_detected` | boolean: max heel world.y − baseline > 0.02m | false |
| `heel_lift_magnitude` | max(heel world.y − baseline) during rep | 0.0 |

---

## Frame Reliability — Confidence Signal

```python
import statistics

# Per rep — aggregate frame_reliability from input frames
rep_frames = [f for f in all_frames if f.rep_index == rep_num]
median_frame_reliability = statistics.median([f.frame_reliability for f in rep_frames])

# Overall session
median_frame_reliability_overall = statistics.median([f.frame_reliability for f in all_frames])
```

Passed to the LLM so it can calibrate confidence per rep. Use **median not mean** — more robust to outlier frames with poor visibility.

---

## Consolidated — Cross-Rep Trends

```python
import numpy as np

def trend_slope(values):
    """Linear slope across reps. Positive = worsening, negative = improving."""
    x = np.arange(len(values))
    slope, _ = np.polyfit(x, values, 1)
    return round(slope, 4)

# Apply to key metrics
back_angle_trend    = trend_slope([r['back_data']['back_angle_max'] for r in reps])
depth_trend         = trend_slope([r['depth_data']['knee_angle_min'] for r in reps])
knee_valgus_trend   = trend_slope([r['stability_data']['knee_valgus_distance'] for r in reps])
tempo_trend         = trend_slope([r['tempo_data']['total'] for r in reps])
ankle_df_trend      = trend_slope([r['ankle_data']['dorsiflexion_at_bottom'] for r in reps])
```

| Trend field | Positive slope | Negative slope |
|-------------|---------------|----------------|
| `back_angle_trend` | Lean worsening with fatigue | Lean improving |
| `depth_trend` | Cutting depth as reps increase | Going deeper |
| `knee_valgus_trend` | Cave worsening | Stability improving |
| `tempo_trend` | Slowing down (fatigue) | Speeding up |
| `ankle_dorsiflexion_trend` | Ankle stiffening under load | Dorsiflexion improving |

---

## Output JSON Structure

Full schema with 10-rep example: **`Kinetic_Biomechanics_Output_Schema.json`**

Top-level structure:
```json
{
  "session": { "analysis_id", "exercise", "weight_kg", "rep_count",
               "quality_gate_status", "video_score", "camera_view" },
  "reps": [
    {
      "rep_number": 1,
      "median_frame_reliability": 0.91,
      "error_flags": [],
      "error_values": {},
      "tempo_data": { "eccentric", "pause", "concentric", "total",
                      "tempo_notation", "squat_type" },
      "back_data":  { "back_angle_start", "back_angle_max", "back_angle_at_bottom",
                      "time_warning", "time_excessive", "status",
                      "butt_wink_detected", "butt_wink_severity_deg" },
      "depth_data": { "hip_angle_start", "hip_angle_at_bottom", "hip_angle_min",
                      "knee_angle_start", "knee_angle_at_bottom", "knee_angle_min",
                      "depth_classification", "depth_insufficient_flag" },
      "stability_data": { "knee_valgus_distance", "valgus_phase", "valgus_flag",
                          "heel_lift_detected", "heel_lift_magnitude" },
      "ankle_data": { "dorsiflexion_at_bottom", "foot_turnout_left", "foot_turnout_right" }
    }
  ],
  "consolidated": {
    "total_reps", "median_frame_reliability_overall",
    "posture":          { "back_angle_max_mean", "back_angle_at_bottom_mean",
                          "back_angle_trend", "butt_wink_reps", "status_distribution" },
    "stability":        { "knee_valgus_mean", "knee_valgus_trend",
                          "valgus_flag_reps", "valgus_phase_distribution", "heel_lift_reps" },
    "movement_quality": { "depth_distribution", "knee_angle_min_mean", "depth_trend",
                          "depth_insufficient_reps", "ankle_dorsiflexion_mean",
                          "ankle_dorsiflexion_trend", "foot_turnout_left_mean",
                          "foot_turnout_right_mean" },
    "tempo":            { "eccentric_mean", "pause_mean", "concentric_mean",
                          "total_mean", "total_trend", "tempo_notation_mode" }
  }
}
```

---

## What NOT to Pass to LLM

These fields from the input frame payload are used during computation but **not** included in the output JSON:

| Field | Reason |
|-------|--------|
| `frame_index` | Internal processing artifact |
| `timestamp_ms` | Used for tempo calculation, not needed downstream |
| `rep_index` | Expressed as `rep_number` in output |
| `world_landmarks` | Raw coordinates — too granular for LLM |
| `screen_landmarks` | Same — consumed during computation only |
| `position_tag` | Used to derive at-bottom/at-top metrics, not passed directly |
| Nose (0), Eye (2,5), Elbow (13,14) | Not used — see landmark table above |

---

## Changelog
- May 8, 2026: Initial spec — field definitions, formulas, Python logic for all 4 parameter groups
