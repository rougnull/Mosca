# Simulation Physics and Brain Fixes - 2026-03-12

## Problem Summary

Analyzing the simulation data from `2026-03-12_19_48`, I identified two critical interconnected problems:

### 1. Brain Death (No Motor Response)
**Symptoms:**
- brain_actions = [0.0, 1.5e-15] (essentially zero) for all 50,000 steps
- No forward movement commanded
- Turn signal also effectively zero

**Root Cause:**
The brain was working correctly, but the fly was in a death spiral:
- Fly spawned elevated (Z=4.28mm) with "stretch" pose
- Immediately fell due to gravity
- During fall, moved AWAY from odor source
- Brain sensed DECREASING concentration → forward=0 (correct behavior!)
- Cold start bootstrap (0.1) was too weak to overcome initial instability

### 2. Physics Instability (Ground Penetration & Flipping)
**Symptoms:**
- Roll orientation changed from 90° (upright) to ~0° (upside down)
- Z position dropped below 0 (ground penetration) around step 534
- Fly continued rotating and moving chaotically

**Root Cause Chain:**
1. **Elevated spawn**: Start Z=3mm + "stretch" pose → actual Z=4.28mm
2. **Weak stabilization**: CPG with forward=0 generated only 30% amplitude
3. **Fall and flip**: Gravity pulled fly down, torque caused rotation
4. **No recovery**: Once upside down, adhesion can't help (wrong side)
5. **Penetration**: Physics solver failed with inverted fly → Z < 0

## Data Analysis

### Odor Concentration Trajectory
```
Initial: 2.976
Step 100: 2.964
Step 500: 2.247
Final: 1.942
```
Concentration DECREASED throughout simulation → fly moving away from source

### Position Trajectory
```
Initial: [35.01, 35.01, 4.28]
Step 534: Z crosses 0 (ground penetration)
Final: [31.60, 38.25, -0.28]
```

### Orientation at Ground Penetration
```
Step 529: Z=0.037, roll=-0.7°, pitch=5.5°
Step 534: Z=-0.007, roll=-2.8°, pitch=2.6° (penetration starts)
```

## Solutions Implemented

### Fix 1: Stable Ground Spawn
**File**: `tools/run_physics_based_simulation.py:148-151`

Changed:
```python
# BEFORE
init_pose="stretch",
spawn_pos=start_pos,  # (35, 35, 3.0)

# AFTER
init_pose="tripod",  # Standing pose
spawn_pos=(start_pos[0], start_pos[1], 0.5),  # Lower Z for ground contact
```

**Rationale**:
- "tripod" is a stable standing pose (legs on ground)
- Lower Z (0.5mm) ensures immediate ground contact
- Prevents initial falling phase

### Fix 2: Stronger Cold Start Bootstrap
**File**: `src/controllers/improved_olfactory_brain.py:141`

Changed:
```python
# BEFORE
conc_change = 0.1  # Small positive value

# AFTER
conc_change = 0.5  # Larger value for sufficient initial movement
```

**Rationale**:
- 0.1 was too weak (forward = 0.1 * 10.0 * 1.0 = 1.0, but minimal)
- 0.5 provides stronger initial forward command
- Ensures fly moves forward on first step, establishing positive gradient

### Fix 3: Higher CPG Baseline Amplitude
**File**: `src/controllers/cpg_controller.py:128, 249, 215`

Changed:
```python
# BEFORE
amplitude = 0.3 + 0.7 * abs(forward)  # 30% baseline

# AFTER
amplitude = 0.5 + 0.5 * abs(forward)  # 50% baseline
```

**Rationale**:
- 30% amplitude was insufficient for stable standing
- 50% baseline provides better stabilization even when forward=0
- Prevents tipping/flipping during low-activity periods

### Fix 4: Debug Logging
**File**: `src/controllers/improved_olfactory_brain.py:99-103, 150-156, 169-171`

Added debug prints for first 3 brain steps:
- Position and heading inputs
- Odor concentrations (center, left, right)
- Gradient differences
- Motor signal outputs

**Purpose**: Verify brain is receiving correct inputs and generating expected outputs

## Expected Behavior After Fixes

1. **Stable Spawn**: Fly starts on ground in standing pose
2. **Immediate Forward Motion**: Cold start bootstrap (0.5) triggers forward movement
3. **Positive Gradient**: Movement toward source creates increasing concentration
4. **Sustained Chemotaxis**: Brain receives positive dC/dt → continues forward
5. **Bilateral Steering**: Turn signal guides fly toward source
6. **Ground Contact Maintained**: Higher CPG amplitude prevents instability
7. **No Penetration**: Proper physics with adhesion keeps Z ≥ 0

## Test Recommendations

Run new simulation and verify:

```bash
python tools/run_physics_based_simulation.py
```

Check in analysis:
1. **Z position**: Should stay ≥ 0 throughout
2. **Roll orientation**: Should stay near 90° (±5°)
3. **Brain actions**: forward should be > 0 in early steps
4. **Odor concentration**: Should INCREASE (approaching source)
5. **Debug output**: Check first 3 steps show proper inputs/outputs

## Technical Notes

### Why The Previous Fix Didn't Work

The previous commit (2694076) added the cold start bootstrap (0.1) but didn't address:
- Elevated spawn position causing initial fall
- Weak CPG stabilization (30% amplitude)
- Bootstrap value too small for reliable initiation

### Physics Stability Requirements

For stable ground locomotion in FlyGym:
1. Spawn with legs on ground (Z ≤ 1mm)
2. Use standing pose ("tripod" or "zero")
3. Enable adhesion (already done)
4. Maintain sufficient joint oscillation amplitude (≥ 50%)
5. Have non-zero motor commands for active stabilization

### Brain Temporal Gradient Logic

The brain correctly uses dC/dt (concentration change) for forward command:
- Positive dC/dt (approaching source) → forward > 0
- Negative dC/dt (leaving source) → forward = 0
- Zero dC/dt (stationary or parallel) → forward = 0

This prevents the fly from "overshooting" into the source and walking in place.

## Files Modified

1. `src/controllers/improved_olfactory_brain.py` - Bootstrap value and debug logging
2. `src/controllers/cpg_controller.py` - CPG amplitude baseline
3. `tools/run_physics_based_simulation.py` - Spawn pose and position
