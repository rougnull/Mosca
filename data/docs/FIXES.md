# Fixes and Solutions - Mosca Project

**Last Updated**: 2026-03-12
**Status**: All critical issues resolved

---

## Overview

This document consolidates all fixes applied to the physics-based simulation system, particularly focusing on `run_physics_based_simulation.py` and related components.

---

## Issue 1: Optional Dependencies (tqdm)

**Error:**
```
ModuleNotFoundError: No module named 'tqdm'
```

**Root Cause:**
- tqdm was required but not essential for core functionality
- Script failed completely if tqdm wasn't installed

**Solution:**
- Wrapped tqdm import in try-except with fallback
- Added `HAS_TQDM` flag for conditional usage
- Implemented simple progress display (5% intervals) when tqdm unavailable

**Code Pattern:**
```python
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = None

# Usage
if HAS_TQDM:
    iterator = tqdm(range(num_steps))
else:
    iterator = range(num_steps)
    # Print progress manually at 5% intervals
```

**Files Modified:**
- `tools/run_physics_based_simulation.py`
- `tools/run_complete_3d_simulation.py`

**Commit:** 68e712f

---

## Issue 2: Import Dependencies (numpy, FlyGym, Project Components)

**Error:**
```python
ModuleNotFoundError: No module named 'numpy'
# or
ModuleNotFoundError: No module named 'flygym'
```

**Root Cause:**
- Project components (OdorField, OlfactoryBrain, BrainFly) imported before dependency check
- These components require numpy, causing cryptic errors
- Error messages didn't guide users to install dependencies

**Solution:**
- Moved all numpy-dependent imports inside FlyGym try-except block
- Created comprehensive error message with installation instructions
- Set imported names to None to prevent NameError

**Code Pattern:**
```python
try:
    from flygym import Fly, Camera, SingleFlySimulation
    import numpy as np
    # Import project components that require numpy
    from olfaction.odor_field import OdorField
    from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
    from controllers.brain_fly import BrainFly
    HAS_FLYGYM = True
except ImportError as e:
    print("\n[ERROR] Required dependencies not available")
    print("\nThis script requires:")
    print("  - FlyGym: pip install flygym")
    print("  - NumPy: pip install numpy")
    print("\nInstall all dependencies with:")
    print("  pip install flygym numpy")
    HAS_FLYGYM = False
```

**Files Modified:**
- `tools/run_physics_based_simulation.py:46-70`

**Commit:** 63bc504

---

## Issue 3: BrainFly Architecture

**Error:**
```
AttributeError: 'BrainFly' object has no attribute '...'
```

**Root Cause:**
- Incorrect usage pattern: created separate Fly and BrainFly objects
- BrainFly not properly initialized with parent Fly parameters
- Called brain_fly.step() on incorrectly initialized object
- Misunderstanding: BrainFly IS a Fly, not a wrapper around Fly

**Solution:**
- Use BrainFly as direct Fly subclass (it inherits from flygym.Fly)
- Initialize BrainFly with ALL Fly parameters
- Pass BrainFly directly to SingleFlySimulation
- Call fly.step(obs) to get brain-controlled actions

**Correct Pattern:**
```python
# Create BrainFly (inherits from Fly)
self.fly = BrainFly(
    brain=self.brain,
    odor_field=self.odor_field,
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
    motor_mode="direct_joints"
)

# Use BrainFly directly in simulation
self.sim = SingleFlySimulation(
    fly=self.fly,  # BrainFly, not separate Fly
    arena=FlatTerrain(),
    timestep=timestep,
)

# In simulation loop
action = self.fly.step(obs)  # BrainFly handles sensing + motor conversion
```

**Key Insight:**
```
BrainFly extends Fly:
  - Inherits all Fly functionality
  - Adds olfactory sensing via odor_field
  - Adds brain-controlled motor commands
  - step() method: obs → sense odor → brain decision → motor action
```

**Files Modified:**
- `tools/run_physics_based_simulation.py:139-148, 197`

**Commit:** 6fb7c3c

---

## Issue 4: Camera API and Mandatory Rendering

**Error:**
```python
TypeError: Camera.__init__() got an unexpected keyword argument 'name'
```

**Root Cause:**
1. Camera initialized with incorrect API parameters (`name`, `window_size`)
2. Missing required parameters (`fly`, `camera_id`)
3. Rendering was mandatory - no way to run physics-only simulation
4. Camera errors blocked all simulations

**Solution:**

### 4.1 Made Rendering Optional (Default: Disabled)

Added `enable_rendering` parameter to constructor:
```python
def __init__(self, ..., enable_rendering=False):
    self.enable_rendering = enable_rendering
```

Rationale:
- Most use cases only need physics simulation data
- Rendering is slower and can fail
- Separates concerns: physics vs visualization

### 4.2 Fixed Camera API

**Incorrect (Old):**
```python
Camera(
    name="cam_front",         # ❌ Doesn't exist
    window_size=(1920, 1080)  # ❌ Should be 'fps'
)
```

**Correct (New):**
```python
Camera(
    fly=self.fly,                    # ✅ Required: attach to fly
    camera_id="Animat/camera_left",  # ✅ Required: mount point
    play_speed=0.1,                  # ✅ Optional
    fps=render_fps,                  # ✅ Required for video
)
```

### 4.3 Conditional Camera Creation

```python
sim_kwargs = {
    "fly": self.fly,
    "arena": FlatTerrain(),
    "timestep": timestep,
}

if enable_rendering:
    try:
        camera = Camera(
            fly=self.fly,
            camera_id="Animat/camera_left",
            play_speed=0.1,
            fps=render_fps,
        )
        sim_kwargs["cameras"] = [camera]
        print("[INFO] Rendering enabled with camera")
    except Exception as e:
        print(f"[WARNING] Could not initialize camera: {e}")
        print("[INFO] Continuing without camera (rendering disabled)")
        self.enable_rendering = False
else:
    print("[INFO] Rendering disabled - running physics simulation only")

self.sim = SingleFlySimulation(**sim_kwargs)
```

### 4.4 Command-Line Interface

```python
parser.add_argument("--enable-render", action="store_true",
                   help="Enable video rendering with camera")
```

**Usage:**
```bash
# Default: physics-only (fast, no camera errors)
python tools/run_physics_based_simulation.py --duration 10

# Optional: with rendering
python tools/run_physics_based_simulation.py --duration 10 --enable-render
```

**Files Modified:**
- `tools/run_physics_based_simulation.py:91, 113-117, 155-182, 264-344, 414-417, 439`

**Commit:** 46a3113

---

## FlyGym Camera API Reference

### Camera Types Available

1. **Camera** - Standard camera
2. **YawOnlyCamera** - Yaw-stabilized
3. **ZStabilizedCamera** - Head-stabilized

### Required Parameters

```python
Camera(
    fly=fly_object,              # Fly instance (required)
    camera_id="Animat/camera_left",  # Camera mount point (required)
    play_speed=0.1,              # Playback speed (optional)
    fps=30,                      # Frame rate (required for video)
)
```

### Available Camera Mount Points

From FlyGym MuJoCo model:
- `"Animat/camera_left"`
- `"Animat/camera_right"`
- `"Animat/camera_top"`
- `"Animat/camera_front"`

---

## Best Practices Established

### 1. Optional Dependencies Pattern

```python
try:
    import optional_module
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False
    optional_module = None

# Usage with fallback
if HAS_MODULE:
    # Enhanced version
else:
    # Fallback version
```

### 2. Class Inheritance Pattern

When subclass extends parent:
```python
class Child(Parent):
    def __init__(self, child_params, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Pass parent params
        # Child-specific initialization
```

Use it like:
```python
obj = Child(child_params, parent_param1, parent_param2, ...)
```

NOT:
```python
parent = Parent(parent_param1, ...)
child = Child(child_params)  # Wrong! Missing parent initialization
```

### 3. Clear Error Messages

**Bad:**
```
Traceback (most recent call last):
  File "script.py", line 416, in <module>
ModuleNotFoundError: No module named 'numpy'
```

**Good:**
```
Error: Required dependencies not available: No module named 'numpy'

This script requires:
  - FlyGym: pip install flygym
  - NumPy: pip install numpy

Install all dependencies with:
  pip install flygym numpy
```

### 4. Separation of Concerns

Physics simulation should be independent of rendering:
```python
# Wrong: Always requires camera
sim = SingleFlySimulation(fly, arena, timestep, cameras=[...])

# Right: Camera is optional
if enable_rendering:
    sim_kwargs["cameras"] = [camera]
sim = SingleFlySimulation(**sim_kwargs)
```

---

## Testing Checklist

- [x] Script imports without tqdm ✓
- [x] Script shows clear error without FlyGym/numpy ✓
- [x] Script shows help even without dependencies ✓
- [x] Syntax validation passes ✓
- [x] BrainFly properly integrated ✓
- [x] Camera API matches FlyGym documentation ✓
- [x] Rendering is optional (default: disabled) ✓
- [x] Physics-only simulation works without camera ✓
- [x] Graceful error handling for camera failures ✓
- [x] Command-line flag `--enable-render` added ✓

---

## Summary

| Issue | Status | Solution |
|-------|--------|----------|
| 1. tqdm import error | ✅ Fixed | Made optional with fallback progress display |
| 2. numpy import error | ✅ Fixed | Wrapped all numpy-dependent imports together |
| 3. BrainFly architecture | ✅ Fixed | Use BrainFly directly as Fly subclass |
| 4. Camera API error | ✅ Fixed | Corrected Camera parameters + made rendering optional |

**Result**: `run_physics_based_simulation.py` now runs successfully without any camera or import errors. Physics simulation is separated from rendering.

---

## Related Files

- `tools/run_physics_based_simulation.py` - Main physics simulation script
- `src/controllers/brain_fly.py` - BrainFly implementation (Fly subclass)
- `src/controllers/improved_olfactory_brain.py` - Olfactory brain controller
- `src/olfaction/odor_field.py` - Odor field model

## Issue 5: BrainFly Observation Extraction

**Date**: 2026-03-12

**Error:**
Brain generating zero motor commands despite working correctly in isolation.

**Symptoms:**
- Forward action: 1.0 at step 0, then 0.0 for all remaining steps
- Turn action: ~1.5e-15 (essentially 0) throughout simulation
- Brain isolated tests showed proper turn signals (e.g., -0.088)

**Root Cause:**
BrainFly's observation extraction methods were incompatible with SingleFlySimulation's observation structure.

SingleFlySimulation provides:
```python
obs["fly"] = tuple/list containing:
    [0] = position: np.ndarray([x, y, z])
    [1] = quaternion: np.ndarray([w, x, y, z])
    [2] = euler: np.ndarray([roll, pitch, yaw])
```

BrainFly was looking for:
- `obs["fly_orientation"]` - NOT PROVIDED
- `obs["fly"]["position"]` - WRONG (expected dict, got tuple)

**Result**: Methods returned fallback values (heading=0, position=[0,0,0]), breaking bilateral sensing geometry.

**Solution:**

### Fixed `_extract_heading()` in brain_fly.py

Added PRIMARY check for SingleFlySimulation tuple structure:

```python
def _extract_heading(self, obs: Dict[str, Any]) -> float:
    try:
        # SingleFlySimulation structure (PRIMARY)
        if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 3:
            # obs["fly"][2] = Euler angles [roll, pitch, yaw]
            orientation = obs["fly"][2]
            if hasattr(orientation, '__len__') and len(orientation) >= 3:
                return float(orientation[2])  # yaw
        # ... fallbacks for other structures
```

### Fixed `_extract_head_position()` in brain_fly.py

```python
def _extract_head_position(self, obs: Dict[str, Any]) -> np.ndarray:
    try:
        # SingleFlySimulation structure (PRIMARY)
        if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 1:
            position = obs["fly"][0]
            if hasattr(position, '__len__') and len(position) >= 3:
                return np.array(position)
        # ... fallbacks
```

**Files Modified:**
- `src/controllers/brain_fly.py:114-192` - Fixed observation extraction
- `tools/run_physics_based_simulation.py:492` - Fixed spawn_pos Z (3.0→0.5)

**Commit:** Multiple commits 2026-03-12

---

## Issue 6: Physics Instability and Ground Penetration

**Date**: 2026-03-12

**Symptoms:**
- Z position dropped below 0 (ground penetration) around step 534
- Roll orientation changed from 90° (upright) to ~0° (upside down)
- Fly moved AWAY from odor source (concentration decreased)
- Brain actions essentially zero for entire simulation

**Root Cause Chain:**
1. **Elevated spawn**: Z=3mm + "stretch" pose → actual Z=4.28mm
2. **Weak stabilization**: CPG with forward=0 generated only 30% amplitude
3. **Fall and flip**: Gravity pulled fly down, torque caused rotation
4. **No recovery**: Once upside down, adhesion can't help (wrong side)
5. **Penetration**: Physics solver failed with inverted fly

**Data Analysis:**
```
Odor concentration: 2.976 → 1.942 (DECREASING)
Position: [35.01, 35.01, 4.28] → [31.60, 38.25, -0.28]
Step 534: Z crosses 0 (ground penetration)
```

**Solution:**

### Fix 1: Stable Ground Spawn
```python
# BEFORE
init_pose="stretch",
spawn_pos=(35, 35, 3.0)

# AFTER
init_pose="tripod",  # Stable standing pose
spawn_pos=(35, 35, 0.5),  # Lower Z for ground contact
```

**Rationale**: "tripod" is stable standing pose, lower Z prevents fall

### Fix 2: Stronger Cold Start Bootstrap
```python
# BEFORE (in improved_olfactory_brain.py:141)
conc_change = 0.1  # Too weak

# AFTER
conc_change = 0.5  # Sufficient initial movement
```

**Rationale**: 0.5 provides stronger initial forward command, establishes positive gradient

### Fix 3: Higher CPG Baseline Amplitude
```python
# BEFORE (in cpg_controller.py)
amplitude = 0.3 + 0.7 * abs(forward)  # 30% baseline

# AFTER
amplitude = 0.5 + 0.5 * abs(forward)  # 50% baseline
```

**Rationale**: 50% baseline prevents tipping/flipping during low-activity

**Files Modified:**
- `tools/run_physics_based_simulation.py:148-151` - Spawn pose and position
- `src/controllers/improved_olfactory_brain.py:141` - Bootstrap value
- `src/controllers/cpg_controller.py:128,249,215` - CPG amplitude

**Physics Stability Requirements:**
1. Spawn with legs on ground (Z ≤ 1mm)
2. Use standing pose ("tripod" or "zero")
3. Enable adhesion
4. Maintain sufficient amplitude (≥ 50%)
5. Have non-zero motor commands for active stabilization

**Commit:** Multiple commits 2026-03-12

---

## Issue 7: Low Forward Action and Progressive Sinking

**Date**: 2026-03-12

**Symptoms:**
- Forward action mean: 0.00085 (essentially zero)
- Z-axis: 1.783mm → 0.263mm (dropped 1.52mm over 5 seconds)
- Ground contact: 63.3% of time with Z < 0.3mm
- Movement: Only 7mm traveled in 5 seconds

**Root Cause:**
Negative feedback loop with three interconnected issues:
1. **Brain too insensitive**: temporal_gradient_gain=10.0 required dC > 0.1 for forward=1.0 (impossible with actual dC ≈ 5.8e-05)
2. **Weak leg support**: CPG amplitude baseline of 0.5 insufficient when forward ≈ 0
3. **Permanently flexed femur**: offset=-0.8 rad kept legs bent, unable to support body

**Data Analysis:**
```
Forward mean: 0.00085
Mean dC/dt: 5.8e-05 (extremely small)
With gain=10: forward = clip(5.8e-05 * 10) = 0.00058
With gain=50: forward = clip(5.8e-05 * 50) = 0.0029 (5x better)
```

**Solution:**

### Fix 1: Brain Sensitivity (temporal_gradient_gain)
```python
# tools/run_physics_based_simulation.py:141
# BEFORE
temporal_gradient_gain=10.0

# AFTER
temporal_gradient_gain=50.0  # 5x more sensitive
```

### Fix 2: CPG Amplitude Baseline
```python
# src/controllers/cpg_controller.py:129
# BEFORE
amplitude = 0.5 + 0.5 * abs(forward)

# AFTER
amplitude = 0.7 + 0.3 * abs(forward)  # 40% more at forward≈0
```

### Fix 3: Femur Extension
```python
# src/controllers/cpg_controller.py:163,166
# BEFORE
offset = -0.8  # Very flexed
angle = offset + amp * 0.3

# AFTER
offset = -0.5  # More extended
angle = offset + amp * 0.4  # Better support
```

**Validation Results:**
```
Forward mean: 0.0448 (vs 0.00085) → 52x improvement
Z-axis: 1.78→2.26mm (RISING vs sinking)
Ground contact: 0% (vs 63.3%)
```

**Files Modified:**
- `tools/run_physics_based_simulation.py:141` - temporal_gradient_gain
- `src/controllers/cpg_controller.py:129` - amplitude baseline
- `src/controllers/cpg_controller.py:163,166` - femur offset and extension

**Commit:** e602227, subsequent fixes 2026-03-12

---

## Summary Table - All Issues

| Issue | Date | Status | Key Fix |
|-------|------|--------|---------|
| 1. tqdm import | - | ✅ Fixed | Made optional with fallback |
| 2. numpy/FlyGym import | - | ✅ Fixed | Wrapped imports, clear errors |
| 3. BrainFly architecture | - | ✅ Fixed | Use as Fly subclass directly |
| 4. Camera API | - | ✅ Fixed | Corrected params, made optional |
| 5. Observation extraction | 2026-03-12 | ✅ Fixed | Handle tuple structure |
| 6. Physics instability | 2026-03-12 | ✅ Fixed | Stable spawn, higher CPG amp |
| 7. Low forward/sinking | 2026-03-12 | ✅ Fixed | Increase gain, amplitude, femur |

---
