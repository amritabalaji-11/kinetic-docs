# Biomechanics JSON Schema — Database Column Definition

The `biomechanics_json` column in `form_analysis_results` stores the complete output from the MediaPipe + biomechanics analysis pipeline. This is a JSONB column in PostgreSQL.

---

## Top-Level Structure

```json
{
  "metadata": { ... },
  "set_summary": { ... },
  "reps": [ ... ]
}
```

---

## Field Breakdown

### `metadata`
```json
{
  "exercise": "goblet_squat",
  "total_reps": 3,
  "processing_timestamp": "2026-05-08T11:40:22.521453Z",
  "schema_version": "1.0"
}
```

### `set_summary`
Contains aggregated metrics across all reps:
- `reps_analysed` (int)
- `avg_form_score` (0–100)
- `rep_timing` — duration stats (total_reps, avg_duration_s, fastest_rep_s, slowest_rep_s, set_start_ms, set_end_ms)
- `set_integrity` — fatigue detection, degrading_metrics array, trend_direction
- `trends` — form_score, knee_depth, torso_lean, valgus_max, lr_symmetry (each with values array + slope)
- `rep_scores` — arrays of scores for each rep (form_score, posture, stability, movement_quality, tempo, rep_indices, rep_counts, rep_durations_s)
- `set_level_cue` (string) — coaching cue for the set

### `reps` (array of rep objects)
Each rep contains:
- `rep_index` (int) — 1-based index
- `rep_count` (int) — absolute count
- `rep_time` — start_ms, end_ms, duration_ms, duration_s
- `form_score` (0–100)
- `keyframe_indices` — top_of_rep, mid_descent, bottom, mid_ascent, error_peak_frames array
- `scorecard` — metrics evaluated (knee_depth, torso_lean, hip_flexion, valgus_max, shin_angle, lr_symmetry, hip_drop, foot_angle, hip_shoulder_align)
  - Each metric has: value_deg, target, metric_score, weight, status (pass/warn/flag), flag (null/minor/significant)
- `phases` — descent, bottom, ascent (each with frame_count, weighted_angles dict, anomaly_frames array)
- `symmetry` — left/right comparisons (knee_flexion, hip_flexion, valgus, shin_angle, foot_angle) with delta_deg and severity
- `error_onset` — tracks when errors first appear in the movement
- `coaching_dimensions` — posture, stability, movement_quality, tempo (each with score, color, positive/critical text, raw data)
- `llm_context` — preformatted for Claude system prompt (form_score, top_errors, caution_items, strengths, priority_cue, persona)

---

## Database Column Definition

```sql
ALTER TABLE form_analysis_results 
ADD COLUMN biomechanics_json JSONB;

-- Optional: index for fast queries by form_score or rep count
CREATE INDEX idx_biomechanics_form_score 
  ON form_analysis_results 
  USING gin ((biomechanics_json->'set_summary'->>'avg_form_score'));
```

---

## Example Query

```sql
-- Get average form score for a user
SELECT 
  form_analysis_id,
  (biomechanics_json->'set_summary'->>'avg_form_score')::int as form_score,
  (biomechanics_json->'metadata'->>'exercise') as exercise
FROM form_analysis_results
WHERE user_id = 'user_001'
ORDER BY created_at DESC;
```

---

## Notes

- All angles are in degrees
- All timestamps use UTC (ISO 8601 format)
- The `llm_context` section is pre-extracted for use in Claude prompts — no further processing needed
- The `coaching_dimensions` includes both raw data and human-readable coaching text
- For OpenCV Part 2, use `reps[0].rep_index` = worst rep to extract the frame at `reps[0].rep_time.start_ms`
