# Brain-Motor Connection Fix - 2026-03-12

## Problem Summary

The simulation from `2026-03-12_20_04` showed that the brain was generating essentially zero motor commands:
- **Forward action**: 1.0 on step 0, then 0.0 for all remaining steps
- **Turn action**: ~1.5e-15 (essentially 0) throughout entire simulation

However, testing the brain in isolation showed it SHOULD generate proper turn signals (e.g., -0.088).

## Root Cause Analysis

### The Bug

**BrainFly's observation extraction methods were incompatible with SingleFlySimulation's observation structure.**

#### What SingleFlySimulation Provides

```python
obs["fly"] = tuple/list containing:
    [0] = position: np.ndarray([x, y, z])           # Body position in mm
    [1] = quaternion: np.ndarray([w, x, y, z])      # Orientation as quaternion
    [2] = euler: np.ndarray([roll, pitch, yaw])     # Orientation as Euler angles
    [3] = ... (other data)
```

#### What BrainFly Was Looking For

The `_extract_heading()` and `_extract_head_position()` methods were checking for:
- `obs["fly_orientation"]` - NOT PROVIDED
- `obs["orientation"]` - NOT PROVIDED
- `obs["fly"]["position"]` - WRONG (expects dict, got tuple)
- `obs["fly_velocity"]` - NOT PROVIDED

**Result**: Both methods failed and returned default/fallback values (heading=0 or last_heading, position=[0,0,0]).

### Why This Broke Bilateral Sensing

The ImprovedOlfactoryBrain uses **bilateral olfactory sensing** for turning:

1. Samples odor at three points:
   - **Center**: Current position
   - **Left**: `position + 1.2mm * [cos(heading + π/2), sin(heading + π/2), 0]`
   - **Right**: `position + 1.2mm * [cos(heading - π/2), sin(heading - π/2), 0]`

2. Computes turn signal: `turn = 0.8 * clip(conc_left - conc_right, -1, 1)`

**With incorrect heading=0**:
- Left position: `position + [0, 1.2, 0]` (always points North)
- Right position: `position + [0, -1.2, 0]` (always points South)

This is **completely wrong** when the fly is actually facing, say, 47.9° (Northeast). The bilateral sensors were not perpendicular to the actual heading, so the gradient calculation was meaningless.

### Impact Chain

```
Incorrect obs extraction
    ↓
Heading = 0 (or last known)
    ↓
Bilateral sensors misaligned
    ↓
Gradient calculation wrong
    ↓
Turn signal ≈ 0 instead of proper value
    ↓
No steering → fly can't orient toward source
```

## The Fix

### 1. Fixed `_extract_heading()` in brain_fly.py

**File**: `src/controllers/brain_fly.py` lines 142-192

Added PRIMARY check for SingleFlySimulation structure:

```python
def _extract_heading(self, obs: Dict[str, Any]) -> float:
    try:
        # Opción 1: SingleFlySimulation structure (PRIMARY)
        if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 3:
            # obs["fly"][2] = orientation as Euler angles [roll, pitch, yaw]
            orientation = obs["fly"][2]
            if hasattr(orientation, '__len__') and len(orientation) >= 3:
                return float(orientation[2])  # yaw is third element

        # ... (other fallbacks for different obs structures)
```

**Key Changes**:
- Check if `obs["fly"]` is a tuple/list (not dict)
- Extract `obs["fly"][2]` for Euler angles
- Return `obs["fly"][2][2]` (yaw component)
- Added proper type and length checks

### 2. Fixed `_extract_head_position()` in brain_fly.py

**File**: `src/controllers/brain_fly.py` lines 114-148

Added PRIMARY check for SingleFlySimulation structure:

```python
def _extract_head_position(self, obs: Dict[str, Any]) -> np.ndarray:
    try:
        # Opción 1: SingleFlySimulation structure (PRIMARY)
        if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 1:
            # obs["fly"][0] = position array [x, y, z]
            position = obs["fly"][0]
            if hasattr(position, '__len__') and len(position) >= 3:
                return np.array(position)

        # ... (other fallbacks for different obs structures)
```

**Key Changes**:
- Check if `obs["fly"]` is a tuple/list
- Extract `obs["fly"][0]` for position
- Convert to numpy array and return

### 3. Fixed Spawn Height in main()

**File**: `tools/run_physics_based_simulation.py` line 492

```python
# BEFORE
start_pos=(35.0, 35.0, 3.0),

# AFTER
start_pos=(35.0, 35.0, 0.5),  # Lower Z for ground contact
```

**Rationale**: Ensures spawn_pos matches the value set in BrainFly initialization.

### 4. Enhanced Debug Output

**File**: `src/controllers/improved_olfactory_brain.py`

Increased debug steps from 3 to 5 and improved output format to show bootstrap status.

## Expected Behavior After Fix

### Correct Heading Extraction
```
[Brain Step 1]
  Position: [35.015, 35.007, 1.783]
  Heading: 0.8365 rad (47.9°)  ← NOW CORRECT!
  Conc center: 2.756184
  Conc left: 2.670861
  Conc right: 2.780951
  Gradient diff (L-R): -0.110090  ← NOW MEANINGFUL!
  Conc change: 0.5 (bootstrap)
  Motor signal: forward=1.000000, turn=-0.088072  ← PROPER TURN SIGNAL!
```

### Proper Bilateral Sensing

With heading=47.9° (NE direction):
- **Left sensor**: Points ~138° (NW) - perpendicular left
- **Right sensor**: Points ~-42° (SE) - perpendicular right

This correctly samples the gradient **across** the fly's body, enabling proper chemotaxis steering.

### Simulation Behavior

The next simulation should show:
1. ✅ Proper heading extraction from first step
2. ✅ Non-zero turn signals (typically -0.1 to 0.1 range)
3. ✅ Brain actions: `[forward, turn]` both meaningful
4. ✅ Fly steers toward odor source (increasing concentration)
5. ✅ Stable ground contact (Z ≥ 0)
6. ✅ Smooth chemotaxis trajectory

## Technical Details

### SingleFlySimulation vs HybridTurningController

FlyGym provides different simulation types with different obs structures:

| Simulation Type | obs["fly"] Structure | Use Case |
|-----------------|---------------------|----------|
| **SingleFlySimulation** | `tuple(position, quat, euler, ...)` | Basic physics sim |
| **HybridTurningController** | `dict{"position": ..., "orientation": ...}` | High-level control |
| **MultiModalFly** | Various nested dicts | Advanced sensing |

**Our Implementation**: Uses `SingleFlySimulation` (basic physics) → Need tuple access pattern.

### Why Multiple Fallbacks?

The extraction methods maintain **multiple fallback patterns** to support:
1. **SingleFlySimulation** (current use case) - tuple structure
2. **HybridTurningController** (potential future use) - dict structure
3. **Legacy compatibility** - velocity-based heading estimation
4. **Graceful degradation** - return last known or default values

This design ensures the code works across different FlyGym simulation types.

## Testing Verification

To verify the fix:

```bash
# Run new simulation
python tools/run_physics_based_simulation.py

# Check debug output shows:
# - Correct heading values (not 0.0)
# - Non-zero turn signals
# - Meaningful gradient differences

# Check analysis shows:
# - brain_actions with both forward and turn components
# - Odor concentration INCREASING (not decreasing)
# - Z position stays ≥ 0
# - Trajectory curves toward source
```

## Files Modified

1. **src/controllers/brain_fly.py**:
   - `_extract_heading()`: Added SingleFlySimulation structure handling
   - `_extract_head_position()`: Added SingleFlySimulation structure handling

2. **tools/run_physics_based_simulation.py**:
   - Fixed hardcoded `start_pos` Z value (3.0 → 0.5)

3. **src/controllers/improved_olfactory_brain.py**:
   - Extended debug output from 3 to 5 steps
   - Improved debug message formatting

## Related Issues

This bug was related to but distinct from:
- **Previous issue**: Elevated spawn causing fall → Fixed by changing pose and Z
- **This issue**: Observation structure mismatch → Fixed by updating extraction methods

Both issues contributed to simulation failure, but operated at different levels:
- Physics level: Spawn position/pose
- Control level: Observation parsing

## Prevention

To prevent similar issues in the future:

1. **Document observation structures** clearly for each simulation type
2. **Add unit tests** for observation extraction with different structures
3. **Log extraction results** during debugging to verify correct values
4. **Type hints** for obs parameter showing expected structure

## Conclusion

The brain-motor connection was working correctly at the algorithmic level, but the interface between FlyGym observations and BrainFly's extraction methods was broken. The fix ensures BrainFly correctly interprets SingleFlySimulation's tuple-based observation structure, enabling proper bilateral olfactory sensing and chemotaxis behavior.
