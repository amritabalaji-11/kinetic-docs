# Kinetic — OpenCV Wrapper Specification (FINAL)
**Task:** S3-W5-08  
**Owner:** Squad 3  
**Date:** May 23, 2026  
**Approach:** Option C — Hybrid (Root Cause + Fault Details)  
**Consumes:** Haiku output (worst_rep_index, causal_chains, fault_detail) + Biomechanics JSON + Video file  
**Outputs:** Single annotated PNG frame (worst rep bottom position)

---

## Overview

Takes the worst-rep frame from a session and overlays:
- **Root cause** (if causal_confidence > 70%) — highlighted with separate box + visual indicators
- **Primary fault(s)** — colored zones + angle values + severity
- **Secondary faults** — compact list with confidence badges
- **Skeleton** — joint positions with confidence-scaled opacity
- **Actual vs. Target** — shows variance for coaching clarity
- **Severity indicators** — Green/Amber/Red based on fault_detail + trend

**Fallback:** If causal_chains confidence < 70%, switch to Option A (fault-centric only).

---

## Frame Selection Logic

**Input:** Haiku `worst_rep_index` (0-based array index) + `rep_scores[]` + Biomechanics JSON per rep

```python
def select_worst_rep_frame():
  """Extract worst-rep frame at bottom position using Haiku-computed worst_rep_index."""
  
  # 1. Get worst rep index from Haiku (0-based array index)
  worst_rep_array_index = haiku_output["worst_rep_index"]
  
  # 2. Convert to rep number (1-based) for biomechanics lookup
  worst_rep_number = worst_rep_array_index + 1
  
  # 3. Get biomechanics for that rep
  worst_rep_biomechanics = biomechanics_json["reps"][worst_rep_array_index]
  
  # 4. Extract bottom frame timestamp
  # (timestamp_ms should be in biomechanics output for bottom position)
  bottom_timestamp_ms = worst_rep_biomechanics["timestamp_ms_at_bottom"]
  
  # 5. Convert to frame index (if needed)
  # frame_index = int(bottom_timestamp_ms / 1000 * fps)
  
  # 6. Extract frame from video
  frame = extract_frame_by_timestamp(video_path, bottom_timestamp_ms)
  
  return frame, worst_rep_number, worst_rep_biomechanics
```

**Why use Haiku's worst_rep_index?**
- **Deterministic:** Matches Haiku's scoring exactly — no recalculation needed
- **Efficient:** O(1) lookup instead of O(n) search through rep_scores
- **Consistent:** Ensures OpenCV Part 2 annotates the same rep Haiku identified as worst

---

## Skeleton Drawing

**Input:** `world_landmarks` array (33 MediaPipe joints) from worst rep at bottom frame

**Joints to draw:**
```
Shoulders:    11 (left), 12 (right)
Hips:         23 (left), 24 (right)
Knees:        25 (left), 26 (right)
Ankles:       27 (left), 28 (right)
Heels:        29 (left), 30 (right)
Feet:         31 (left), 32 (right)
```

**Connections (bones):**
```
Torso:  11-23 (L shoulder-hip), 12-24 (R shoulder-hip)
Spine:  11-12 (shoulders), 23-24 (hips)
Left leg: 23-25-27-29
Right leg: 24-26-28-30
```

**Implementation:**

```python
def draw_skeleton(frame, world_landmarks, frame_reliability):
  """Draw skeleton: joints + bones with confidence-scaled opacity."""
  
  h, w = frame.shape[:2]
  
  # Define bone connections
  bones = [
    (11, 23), (12, 24),  # torso
    (11, 12), (23, 24),  # spine
    (23, 25), (25, 27), (27, 29),  # left leg
    (24, 26), (26, 28), (28, 30)   # right leg
  ]
  
  # Convert world coords to screen coords
  screen_joints = {}
  for i in [11, 12, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]:
    wl = world_landmarks[i]
    # Assuming world coords are normalized; scale to frame
    x = int(wl['x'] * w)
    y = int(wl['y'] * h)
    confidence = wl.get('visibility', 0.5)
    screen_joints[i] = (x, y, confidence)
  
  # Draw bones (gray, thin)
  for start_idx, end_idx in bones:
    if start_idx in screen_joints and end_idx in screen_joints:
      x1, y1, conf1 = screen_joints[start_idx]
      x2, y2, conf2 = screen_joints[end_idx]
      
      # Use average confidence for opacity
      avg_conf = (conf1 + conf2) / 2
      alpha = int(200 * avg_conf)  # 0–200 opacity
      
      # Draw line with blending
      overlay = frame.copy()
      cv2.line(overlay, (x1, y1), (x2, y2), 
               color=(128, 128, 128),  # gray
               thickness=2)
      cv2.addWeighted(overlay, alpha/255, frame, 1 - alpha/255, 0, frame)
  
  # Draw joints (gray circles, sized by confidence)
  for idx, (x, y, conf) in screen_joints.items():
    radius = max(3, int(5 * conf))  # 3–5px based on confidence
    
    if conf > 0.5:
      cv2.circle(frame, (x, y), radius, 
                 color=(128, 128, 128), thickness=-1)  # filled
    else:
      cv2.circle(frame, (x, y), radius,
                 color=(128, 128, 128), thickness=1)   # dotted = outline only
  
  return frame
```

---

## Root Cause Visualization (if confidence > 70%)

**Input:** `causal_chains[0]` from Haiku output

**Visual representation:**
- **Yellow box** (top-left area) with root cause details
- **Yellow circle(s)** on frame highlighting the affected joint(s)
- **Text**: Root cause + actual vs. target + chain explanation

```python
def draw_root_cause_box(frame, causal_chain, worst_rep_biomechanics):
  """
  Draw root cause box if confidence > 0.70.
  
  causal_chain = {
    "root_cause": "ankle_dorsiflexion_restricted",
    "chain": "ankle restriction → forward lean → valgus",
    "affected_parameters": ["range_of_motion", "stability"],
    "causal_confidence": 0.75
  }
  """
  
  if causal_chain.get("causal_confidence", 0) < 0.70:
    return frame  # Skip if low confidence
  
  h, w = frame.shape[:2]
  
  # Root cause mapping to parameter + value
  root_param_map = {
    "ankle_dorsiflexion_restricted": {
      "label": "ANKLE DORSIFLEXION LIMITED",
      "value": worst_rep_biomechanics["ankle_data"]["dorsiflexion_at_bottom_deg"],
      "target": 25,
      "unit": "°",
      "joint_indices": [27, 28],  # both ankles
      "color": (0, 255, 255)  # yellow in BGR
    },
    "insufficient_hip_loading": {
      "label": "HIP LOADING INSUFFICIENT",
      "value": worst_rep_biomechanics["depth_data"]["hip_angle_at_bottom"],
      "target": 90,
      "unit": "°",
      "joint_indices": [23, 24],  # both hips
      "color": (0, 255, 255)
    }
    # ... add more mappings as needed
  }
  
  root_cause = causal_chain.get("root_cause")
  root_info = root_param_map.get(root_cause)
  
  if not root_info:
    return frame
  
  # Draw yellow circles on affected joints
  for joint_idx in root_info["joint_indices"]:
    if joint_idx in screen_joints:
      x, y, _ = screen_joints[joint_idx]
      cv2.circle(frame, (x, y), 25, 
                 color=root_info["color"], thickness=3)
  
  # Draw root cause box (top-left)
  box_x, box_y = 20, 20
  box_w, box_h = 280, 100
  
  # Yellow background box
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h),
                color=(0, 255, 255), thickness=-1)
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h),
                color=(0, 200, 200), thickness=2)  # border
  
  # Text content
  font = cv2.FONT_HERSHEY_SIMPLEX
  y_offset = box_y + 20
  
  # Title
  cv2.putText(frame, "ROOT CAUSE [YELLOW]", (box_x + 10, y_offset),
              font, 0.5, (0, 0, 0), 1)
  y_offset += 22
  
  # Root cause label
  cv2.putText(frame, root_info["label"], (box_x + 10, y_offset),
              font, 0.45, (0, 0, 0), 1)
  y_offset += 20
  
  # Actual vs. Target
  variance = root_info["value"] - root_info["target"]
  sign = "+" if variance > 0 else ""
  variance_str = f"Actual: {root_info['value']:.1f}{root_info['unit']} · Target: >{root_info['target']}{root_info['unit']}"
  cv2.putText(frame, variance_str, (box_x + 10, y_offset),
              font, 0.4, (0, 0, 0), 1)
  y_offset += 18
  
  variance_str = f"Variance: {sign}{variance:.1f}{root_info['unit']} {'✗' if abs(variance) > 5 else '✓'}"
  cv2.putText(frame, variance_str, (box_x + 10, y_offset),
              font, 0.4, (0, 0, 0), 1)
  
  return frame
```

---

## Primary Fault Visualization (Largest, Most Visible)

**Input:** `fault_detail[primary_fault]` + corresponding biomechanics values

Primary fault = the one with highest severity OR first in critical_observations

**Color:** Zone-specific (Magenta for knee, Orange for back, Cyan for hip, Yellow for ankle)  
**Severity modifier:** Green/Amber/Red intensity

```python
def get_fault_color_and_severity(fault_name, fault_detail):
  """
  Return (color_bgr, severity) tuple.
  Severity: "GREEN", "AMBER", "RED"
  """
  
  zone_colors = {
    "knee_valgus": (255, 0, 255),           # Magenta
    "insufficient_depth": (255, 0, 255),   # Magenta
    "excessive_forward_lean": (0, 165, 255),  # Orange
    "ankle_dorsiflexion_restricted": (0, 255, 255),  # Yellow
    "heel_lift": (0, 255, 255)              # Yellow
  }
  
  base_color = zone_colors.get(fault_name, (100, 100, 100))
  
  # Determine severity from fault_detail
  severity_text = fault_detail.get("severity", "").lower()
  
  if "within range" in severity_text or "adequate" in severity_text:
    severity = "GREEN"
  elif "warning" in severity_text or "acceptable" in severity_text or "caution" in severity_text:
    severity = "AMBER"
  else:  # restricted, excessive, cave, etc.
    severity = "RED"
  
  # Modify color intensity by severity
  if severity == "GREEN":
    color = base_color  # bright as-is
  elif severity == "AMBER":
    # Desaturate: blend with gray
    gray = sum(base_color) // 3
    color = (
      int(base_color[0] * 0.6 + gray * 0.4),
      int(base_color[1] * 0.6 + gray * 0.4),
      int(base_color[2] * 0.6 + gray * 0.4)
    )
  else:  # RED
    # Saturate: intensify
    color = (
      min(int(base_color[0] * 1.2), 255),
      min(int(base_color[1] * 1.2), 255),
      min(int(base_color[2] * 1.2), 255)
    )
  
  return color, severity

def draw_primary_fault(frame, fault_name, fault_detail, worst_rep_biomechanics, 
                       world_landmarks, screen_joints):
  """Draw primary fault box (center) + zone circles on frame."""
  
  h, w = frame.shape[:2]
  color, severity = get_fault_color_and_severity(fault_name, fault_detail)
  
  # Fault-specific data extraction
  fault_data_map = {
    "knee_valgus": {
      "label": "KNEE VALGUS",
      "value": worst_rep_biomechanics["stability_data"]["knee_valgus_distance"],
      "target": 0.25,
      "unit": "m",
      "joint_indices": [25, 26],  # knees
      "format": "{:.2f}m"
    },
    "excessive_forward_lean": {
      "label": "BACK ANGLE EXCESSIVE",
      "value": worst_rep_biomechanics["back_data"]["back_angle_max"],
      "target": 30,
      "unit": "°",
      "joint_indices": [11, 12, 23, 24],  # shoulders + hips (torso line)
      "format": "{:.1f}°"
    },
    "insufficient_depth": {
      "label": "DEPTH INSUFFICIENT",
      "value": worst_rep_biomechanics["depth_data"]["knee_angle_min"],
      "target": 90,
      "unit": "°",
      "joint_indices": [23, 24],  # hips
      "format": "{:.1f}°"
    }
  }
  
  fault_info = fault_data_map.get(fault_name)
  if not fault_info:
    return frame
  
  # Draw circles on affected joints
  for joint_idx in fault_info["joint_indices"]:
    if joint_idx in screen_joints:
      x, y, _ = screen_joints[joint_idx]
      cv2.circle(frame, (x, y), 30, color=color, thickness=3)
  
  # Draw primary fault box (center-left)
  box_x, box_y = 20, 140
  box_w, box_h = 280, 110
  
  # Colored background
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h),
                color=color, thickness=-1)
  
  # Darker border
  border_color = (max(0, color[0]-50), max(0, color[1]-50), max(0, color[2]-50))
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h),
                color=border_color, thickness=2)
  
  # Text (white for contrast)
  font = cv2.FONT_HERSHEY_SIMPLEX
  y_offset = box_y + 20
  
  # Label
  cv2.putText(frame, f"{fault_info['label']} [{severity}]", (box_x + 10, y_offset),
              font, 0.5, (255, 255, 255), 1)
  y_offset += 22
  
  # Value + Target
  variance = fault_info["value"] - fault_info["target"]
  actual_str = fault_info["format"].format(fault_info["value"])
  target_str = fault_info["format"].format(fault_info["target"])
  
  value_line = f"Actual: {actual_str}  Target: {target_str}"
  cv2.putText(frame, value_line, (box_x + 10, y_offset),
              font, 0.4, (255, 255, 255), 1)
  y_offset += 18
  
  # Variance
  sign = "+" if variance > 0 else ""
  check = "✗" if abs(variance) > 0.05 else "✓"
  variance_str = f"Variance: {sign}{fault_info['format'].format(variance)} {check}"
  cv2.putText(frame, variance_str, (box_x + 10, y_offset),
              font, 0.4, (255, 255, 255), 1)
  y_offset += 18
  
  # Trend + reps affected
  trend = fault_detail.get("trend", "stable")
  reps_affected = fault_detail.get("reps_affected", "?")
  trend_line = f"Trend: {trend} | Reps: {reps_affected}"
  cv2.putText(frame, trend_line, (box_x + 10, y_offset),
              font, 0.38, (255, 255, 255), 1)
  
  return frame
```

---

## Secondary Faults (Compact List)

**Input:** Remaining faults from `fault_detail` (sorted by severity)

```python
def draw_secondary_faults(frame, secondary_faults, fault_detail):
  """Draw compact list of secondary faults (bottom area)."""
  
  if not secondary_faults:
    return frame
  
  h, w = frame.shape[:2]
  
  # Draw box
  box_x, box_y = 20, 270
  box_w = 280
  
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + 70),
                color=(200, 165, 0), thickness=-1)  # amber background
  cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + 70),
                color=(150, 120, 0), thickness=2)  # border
  
  font = cv2.FONT_HERSHEY_SIMPLEX
  y_offset = box_y + 18
  
  cv2.putText(frame, "SECONDARY EFFECTS [AMBER]", (box_x + 10, y_offset),
              font, 0.45, (0, 0, 0), 1)
  y_offset += 18
  
  for fault_name in secondary_faults[:2]:  # Show top 2
    fault_detail_item = fault_detail.get(fault_name, {})
    severity_text = fault_detail_item.get("severity", "stable")
    
    line = f"• {fault_name}: {severity_text}"
    cv2.putText(frame, line, (box_x + 10, y_offset),
                font, 0.38, (0, 0, 0), 1)
    y_offset += 16
  
  return frame
```

---

## Header & Footer

```python
def draw_header(frame, session_metadata, worst_rep_number):
  """Draw session info at top."""
  
  h, w = frame.shape[:2]
  exercise = session_metadata.get("exercise", "exercise")
  weight = session_metadata.get("weight_kg", "?")
  rep_count = session_metadata.get("rep_count", "?")
  
  header_text = f"Rep {worst_rep_number}/{rep_count} · {exercise} {weight}kg · WORST FORM"
  
  cv2.putText(frame, header_text, (20, 20),
              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
  
  # Black background for readability
  cv2.rectangle(frame, (15, 5), (len(header_text) * 8 + 30, 35),
                color=(0, 0, 0), thickness=-1)
  
  cv2.putText(frame, header_text, (20, 25),
              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
  
  return frame

def draw_footer(frame, worst_rep_biomechanics, haiku_output):
  """Draw confidence bar + coaching cue at bottom."""
  
  h, w = frame.shape[:2]
  
  # Confidence bar
  confidence = worst_rep_biomechanics.get("median_frame_reliability", 0.85)
  bar_width = int(w * 0.6)
  filled_width = int(bar_width * confidence)
  
  cv2.rectangle(frame, (20, h - 60), (20 + bar_width, h - 45),
                color=(100, 100, 100), thickness=1)
  cv2.rectangle(frame, (20, h - 60), (20 + filled_width, h - 45),
                color=(0, 255, 0), thickness=-1)
  
  confidence_text = f"Frame Confidence: {confidence:.0%}"
  cv2.putText(frame, confidence_text, (25, h - 48),
              cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
  
  # Coaching cue from Haiku
  if "next_session_focus" in haiku_output:
    focus = haiku_output["next_session_focus"][0] if haiku_output["next_session_focus"] else ""
    coaching_text = f"Next: {focus[:60]}..."
    cv2.putText(frame, coaching_text, (25, h - 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 200, 0), 1)
  
  return frame
```

---

## Full Pipeline

```python
def render_worst_rep_frame(haiku_output, biomechanics_json, video_path, output_path):
  """
  Main entry point: produce annotated worst-rep frame.
  
  Implements Option C: Hybrid (root cause + primary + secondary faults)
  Fallback to Option A if causal_confidence < 0.70
  """
  
  # 1. Get worst rep using Haiku's pre-computed worst_rep_index
  worst_rep_number, worst_rep_biomechanics = select_worst_rep_frame(
    haiku_output["worst_rep_index"], biomechanics_json
  )
  
  # 2. Extract frame
  timestamp_ms = worst_rep_biomechanics["timestamp_ms_at_bottom"]
  frame = extract_frame_by_timestamp(video_path, timestamp_ms)
  h, w = frame.shape[:2]
  
  # 3. Get landmarks for skeleton drawing
  world_landmarks = worst_rep_biomechanics["world_landmarks"]
  screen_landmarks = worst_rep_biomechanics["screen_landmarks"]
  
  # 4. Draw skeleton
  frame = draw_skeleton(frame, world_landmarks, 
                       worst_rep_biomechanics["median_frame_reliability"])
  
  # 5. Extract fault data from Haiku output
  fault_detail = haiku_output["fault_detail"]
  causal_chains = haiku_output.get("causal_chains", [])
  
  # 6. Option C logic: Root cause first (if confident), then primary fault
  if causal_chains and causal_chains[0].get("causal_confidence", 0) > 0.70:
    # Option C: Hybrid
    frame = draw_root_cause_box(frame, causal_chains[0], worst_rep_biomechanics)
    
    # Primary fault = first in critical_observations (type: "root_cause" or highest severity)
    primary_fault = identify_primary_fault(fault_detail, causal_chains[0])
    frame = draw_primary_fault(frame, primary_fault, fault_detail[primary_fault],
                              worst_rep_biomechanics, world_landmarks, screen_joints)
    
    # Secondary faults
    secondary_faults = [f for f in fault_detail.keys() if f != primary_fault and fault_detail[f].get("present")]
    frame = draw_secondary_faults(frame, secondary_faults, fault_detail)
  else:
    # Fallback to Option A: Fault-centric (if causal confidence too low)
    sorted_faults = sorted(fault_detail.items(), 
                          key=lambda x: severity_score(x[1]))
    
    for i, (fault_name, fault_data) in enumerate(sorted_faults[:3]):
      if i == 0:
        frame = draw_primary_fault(frame, fault_name, fault_data, 
                                  worst_rep_biomechanics, world_landmarks, screen_joints)
      else:
        frame = draw_secondary_faults(frame, [fault_name], {fault_name: fault_data})
  
  # 7. Draw header + footer
  frame = draw_header(frame, {
    "exercise": biomechanics_json["session"]["exercise"],
    "weight_kg": biomechanics_json["session"]["weight_kg"],
    "rep_count": biomechanics_json["session"]["rep_count"]
  }, worst_rep_number)
  
  frame = draw_footer(frame, worst_rep_biomechanics, haiku_output)
  
  # 8. Save
  cv2.imwrite(output_path, frame)
  
  return output_path
```

---

## Output & Metadata

**File output:**
- Format: PNG (lossless)
- Filename: `{analysis_id}_worst_rep_frame.png`
- GCS path: `gs://kinetic-videos/analyses/{analysis_id}/worst_rep_frame.png`
- Size: 1920×1080 (HD)

**Metadata sidecar (JSON):**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "worst_rep_number": 5,
  "timestamp_ms": 8500,
  "frame_index": 245,
  "exercise": "goblet_squat",
  "weight_kg": 20,
  "frame_reliability": 0.87,
  "faults_detected": ["knee_valgus"],
  "root_cause": "ankle_dorsiflexion_restricted",
  "causal_confidence": 0.75,
  "generated_at": "2026-05-23T14:32:15Z"
}
```

---

## Dependencies

- **OpenCV (cv2):** Frame loading, drawing, text rendering
- **NumPy:** Coordinate transforms
- **Pillow (PIL):** Optional, for anti-aliased text
- **Video codec:** ffmpeg for reliable frame seeking by timestamp

---

## Edge Cases & Fallbacks

| Scenario | Handling |
|----------|----------|
| causal_confidence < 70% | Switch to Option A (fault-centric) |
| Multiple root causes | Show highest confidence one only |
| Frame reliability < 0.5 | Show warning badge, proceed anyway |
| Missing landmark data | Skip skeleton drawing, show zones only |
| Timestamp out of bounds | Log error, use frame 0 as fallback |

---

## Testing Checkpoints

- [ ] Skeleton draws correctly (joints visible, bones connected)
- [ ] Zone circles highlight correct joints
- [ ] Text is readable (white text on colored backgrounds)
- [ ] Colors accurately reflect severity (Green/Amber/Red)
- [ ] Root cause box appears when causal_confidence > 70%
- [ ] Fallback to Option A when causal_confidence < 70%
- [ ] Footer shows coaching cue from Haiku output
- [ ] Frame saves to GCS with correct metadata
- [ ] Metadata sidecar JSON is valid

---

## Changelog

- May 23, 2026: Final spec — Option C (Hybrid) approach with root cause + primary + secondary faults, fallback to Option A, all hardcoded targets from Biomechanics_Script_Spec.md
