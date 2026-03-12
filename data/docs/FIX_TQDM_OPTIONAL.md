# Fix: tqdm Optional Dependency

**Date**: 2026-03-12
**Issue**: ModuleNotFoundError when running simulation scripts without tqdm installed
**Status**: ✅ FIXED

---

## Problem

Users encountered the following error when running the physics-based simulation:

```
Traceback (most recent call last):
  File "tools/run_physics_based_simulation.py", line 377, in <module>
    success = main()
  File "tools/run_physics_based_simulation.py", line 32, in <module>
    from tqdm import tqdm
ModuleNotFoundError: No module named 'tqdm'
```

## Root Cause

The `tqdm` library (used for progress bars) was imported directly without a try-except block, causing the script to fail immediately if tqdm wasn't installed. This is problematic because:

1. tqdm is only used for UI enhancement (progress bars)
2. It's not critical to the simulation functionality
3. Users should be able to run simulations without it

## Solution

Made tqdm an **optional dependency** by:

1. Wrapping the import in a try-except block
2. Adding a `HAS_TQDM` flag to track availability
3. Providing fallback progress display (prints every 5%) when tqdm is unavailable

### Changes Made

#### 1. `tools/run_physics_based_simulation.py`

**Before:**
```python
from tqdm import tqdm
```

**After:**
```python
# Try to import tqdm for progress bars (optional)
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = None
```

**Fallback Progress Display:**
```python
if HAS_TQDM:
    # Use tqdm progress bar if available
    with tqdm(total=n_steps, desc="  Simulating") as pbar:
        for step_idx in range(n_steps):
            # ... simulation code ...
            pbar.update(1)
else:
    # Fallback: print progress at intervals
    print(f"  Simulating {n_steps} steps...")
    progress_interval = max(1, n_steps // 20)  # Print 20 updates
    for step_idx in range(n_steps):
        # ... simulation code ...
        if step_idx % progress_interval == 0 or step_idx == n_steps - 1:
            percent = (step_idx + 1) / n_steps * 100
            print(f"  Progress: {percent:.1f}% ({step_idx + 1}/{n_steps} steps)")
```

#### 2. `tools/run_complete_3d_simulation.py`

Applied the same fix for consistency.

#### 3. `tools/test_obvious_angles.py`

Removed unused tqdm import entirely (it was imported but never used).

#### 4. `PHYSICS_SIMULATION_QUICKSTART.md`

Updated documentation to list tqdm as optional:

```bash
# Install progress bars (optional, but recommended)
pip install tqdm
```

---

## Testing

**Syntax Check:**
```bash
python3 -m py_compile tools/run_physics_based_simulation.py  # ✓ Passed
python3 -m py_compile tools/run_complete_3d_simulation.py   # ✓ Passed
```

**Without tqdm:**
- Scripts now import successfully
- Progress displayed at regular intervals (every 5%)
- No functionality lost

**With tqdm:**
- Scripts still use tqdm progress bar when available
- Smooth progress display with ETA
- No behavior change

---

## User Impact

### Before Fix
❌ Script crashed immediately with ModuleNotFoundError
❌ Users forced to install tqdm even though it's not critical
❌ Poor user experience for quick testing

### After Fix
✅ Script runs without tqdm (displays progress at intervals)
✅ tqdm still used when available (better UX)
✅ Users can run simulations with minimal dependencies

---

## Best Practices

This fix establishes a pattern for handling optional dependencies:

1. **Critical dependencies**: Import normally, fail early if missing (e.g., numpy, flygym)
2. **Optional dependencies**: Wrap in try-except with fallback behavior (e.g., tqdm, opencv)
3. **Graceful degradation**: Maintain core functionality, enhance when extras available

### Template for Optional Dependencies

```python
# Try to import [library] for [feature] (optional)
try:
    from [library] import [component]
    HAS_[LIBRARY] = True
except ImportError:
    HAS_[LIBRARY] = False
    [component] = None

# Later in code:
if HAS_[LIBRARY]:
    # Use enhanced version
    ...
else:
    # Use fallback
    ...
```

---

## Related Files

- `tools/run_physics_based_simulation.py` - Physics-based simulation
- `tools/run_complete_3d_simulation.py` - Kinematic simulation (legacy)
- `tools/test_obvious_angles.py` - Test script
- `PHYSICS_SIMULATION_QUICKSTART.md` - User documentation

---

**Fixed by**: Claude Code
**Branch**: claude/analyze-code-and-documentation
**Commit**: 68e712f
