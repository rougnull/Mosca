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
