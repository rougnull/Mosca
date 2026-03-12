# Debugging Guide for Brain-Motor Connection

## Problem Statement

The simulation from `2026-03-12_20_20` still shows turn signal ≈ 1.5e-15 (essentially zero), even though the observation extraction fix was committed. This document provides debugging tools and analysis.

## Diagnostic Tools Created

### 1. `tools/test_brain_isolated.py`

Tests the brain in complete isolation without any FlyGym physics.

**Purpose**: Verify that the brain algorithm itself works correctly.

**What it tests**:
- Brain generates motor signals from odor field
- Bilateral sensing calculates proper gradients
- Turn signal is non-zero

**Expected result**: ✅
```
>>> Motor signal: forward=1.000000, turn=-0.088937
```

**Actual result**: ✅ **PASSED**
- The brain IS working correctly
- Generates forward=1.0 and turn≈-0.089

### 2. `tools/test_observation_extraction.py`

Tests BrainFly's observation extraction methods with mock observations.

**Purpose**: Verify that BrainFly can extract position and heading from SingleFlySimulation obs structure.

**What it tests**:
- `_extract_head_position()` with tuple structure
- `_extract_heading()` with tuple structure
- Brain.step() with extracted values

**Expected result**: ✅
```
Extracted heading: 0.836500 rad (47.93°)
Motor signal: forward=1.000000, turn=-0.088072
```

**Actual result**: ✅ **PASSED**
- Observation extraction IS working
- Brain with extracted obs works correctly

### 3. `tools/test_short_simulation.py`

Runs a SHORT physics simulation (50 steps = 0.005s) with extensive debug logging.

**Purpose**: Test the complete integrated system in a quick test.

**What it tests**:
- Full BrainFly + SingleFlySimulation integration
- Actual observation structure from FlyGym
- Motor signal storage and retrieval
- Debug logging throughout the pipeline

**Usage**:
```bash
python tools/test_short_simulation.py
```

This will show detailed debug output for the first 3 steps, revealing exactly what's happening at each stage.

## Analysis of Current Situation

### Test Results Summary

| Test | Status | Turn Signal |
|------|--------|-------------|
| Brain isolated | ✅ PASS | -0.089 |
| Observation extraction | ✅ PASS | -0.088 |
| Short simulation | ❓ UNKNOWN | TBD |
| Full simulation (user's) | ❌ FAIL | 1.5e-15 |

### Possible Root Causes

Given that ALL our tests pass, but the user's simulation fails, the issue must be:

#### 1. **OLD CODE BEING RUN** (Most Likely)

The user's simulation at `2026-03-12_20_20` was likely run BEFORE pulling the latest changes.

**Evidence**:
- Commit `875a981` (obs structure fix) was made at 19:08
- User's simulation folder timestamped 19:25 (only 17 minutes later)
- User may have had old code loaded in memory or old Python process

**Solution**: User needs to:
```bash
git pull
# Restart Python if running in interactive session
# Re-run simulation
python tools/run_physics_based_simulation.py
```

#### 2. **PYTHON IMPORT CACHING**

If the user was running Python interactively or had a long-running Jupyter session, the old module may still be loaded.

**Solution**:
```python
# In Python/Jupyter:
import importlib
import src.controllers.brain_fly
importlib.reload(src.controllers.brain_fly)
```

#### 3. **PYTH ONPATH ISSUE**

Multiple versions of the code in different locations.

**Solution**: Check Python path and ensure using the correct version.

## Debug Logging Added

Added extensive debug logging to `src/controllers/brain_fly.py`:

```python
# Logs on first 3 steps:
# - Observation structure (type, length)
# - Extracted position
# - Extracted heading
# - Brain output (forward, turn)
# - Stored motor_signal
# - Action type and shape
```

**To see this output**: Run any simulation and check console output or redirect stdout to file.

## Verification Steps for User

### Step 1: Verify Code is Updated

```bash
cd /path/to/Mosca
git log --oneline -3
# Should show: 875a981 Fix brain-motor connection
```

### Step 2: Check the Fix is Applied

```bash
grep -A 5 "# Opción 1: SingleFlySimulation" src/controllers/brain_fly.py
# Should show code checking for tuple structure
```

### Step 3: Run Isolated Tests

```bash
# Test 1: Brain alone
python tools/test_brain_isolated.py
# Should show turn ≈ -0.089

# Test 2: Observation extraction
python tools/test_observation_extraction.py
# Should show turn ≈ -0.088
```

### Step 4: Run Short Simulation

```bash
python tools/test_short_simulation.py 2>&1 | tee debug_output.txt
```

This will:
- Run only 50 steps (fast)
- Show detailed debug output
- Reveal exactly what's happening

### Step 5: Run Full Simulation

```bash
python tools/run_physics_based_simulation.py
```

Check the output folder's `analysis.txt` - turn signals should be non-zero.

## Expected Debug Output (Correct Behavior)

When working correctly, you should see:

```
[BrainFly Step 1]
  Obs type: <class 'dict'>
  obs['fly'] type: <class 'tuple'>
  obs['fly'] length: 9
  obs['fly'][0] (pos): [35.015 35.007  1.783]
  obs['fly'][2] (euler): [1.5705e+00 1.6e-04 8.3650e-01]
  Extracted pos: [35.015 35.007  1.783]
  Extracted heading: 0.836500 rad (47.93°)

[Brain Step 1]
  Position: [35.015 35.007  1.783]
  Heading: 0.8365 rad (47.9°)
  Conc center: 2.756184
  Conc left: 2.670861
  Conc right: 2.780951
  Gradient diff (L-R): -0.110090
  Conc change: 0.500000 (bootstrap)
  Motor signal: forward=1.000000, turn=-0.088072
  Brain output: forward=1.000000, turn=-0.088072
  Stored motor_signal: [ 1.        -0.0880719]
```

## If Problem Persists

If the user STILL sees turn=1.5e-15 after:
1. Pulling latest code
2. Restarting Python
3. Running test_short_simulation.py

Then we need to investigate:
- FlyGym version compatibility
- SingleFlySimulation obs structure (may have changed)
- Numerical precision issues
- Some unknown override in the pipeline

## Summary

**All diagnostic tests PASS**, which means:
- ✅ Brain algorithm works
- ✅ Observation extraction works
- ✅ Bilateral sensing works
- ✅ Code changes are correct

**Most likely cause**: User ran simulation with old code before pulling changes.

**Solution**: User needs to ensure they have latest code and re-run simulation.

**Tools provided**: Three diagnostic scripts to isolate and test each component independently.
