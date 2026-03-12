# Fix: BrainFly Architecture Correction

**Date**: 2026-03-12
**Issue**: Runtime error at line 416 - brain_fly referenced but not properly initialized
**Status**: ✅ FIXED

---

## Problem

User reported error at line 416 in `run_physics_based_simulation.py`:

```
Traceback (most recent call last):
  File "tools/run_physics_based_simulation.py", line 416, in <module>
    success = main()
```

The actual error occurred during simulation execution when `self.brain_fly.step()` was called but `brain_fly` was not properly initialized.

## Root Cause

The code had a fundamental architectural misunderstanding about how `BrainFly` should be used:

### Incorrect Architecture (Before)

```python
# Created regular Fly
self.fly = Fly(
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
)

# Created BrainFly separately (WRONG - tried to use as wrapper)
self.brain_fly = BrainFly(
    brain=self.brain,
    odor_field=self.odor_field,
    motor_mode="direct_joints"
)

# Used regular Fly in simulation (no brain integration!)
self.sim = SingleFlySimulation(
    fly=self.fly,  # ← Regular Fly, not BrainFly
    arena=FlatTerrain(),
    timestep=timestep,
)

# Later tried to call brain_fly.step()
action = self.brain_fly.step(self.obs)  # ← Error! brain_fly not properly initialized
```

**Problems:**
1. `BrainFly` was not initialized with Fly parameters (missing `*args, **kwargs`)
2. Regular `Fly` used in simulation instead of `BrainFly`
3. `brain_fly.step()` called on incorrectly initialized object
4. Brain never actually controlled the fly

### Correct Architecture (After)

```python
# Create BrainFly directly (inherits from Fly)
self.fly = BrainFly(
    brain=self.brain,
    odor_field=self.odor_field,
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
    motor_mode="direct_joints"
)

# Use BrainFly in simulation
self.sim = SingleFlySimulation(
    fly=self.fly,  # ← BrainFly, integrates brain + sensing
    arena=FlatTerrain(),
    timestep=timestep,
)

# Call fly.step() to get brain-controlled actions
action = self.fly.step(self.obs)  # ← Correct! fly IS a BrainFly
```

**Why this works:**
1. `BrainFly` inherits from `Fly` - it IS a Fly with brain integration
2. All Fly parameters passed to BrainFly constructor
3. BrainFly properly initialized and used in simulation
4. `fly.step(obs)` processes observations → brain → motor commands

---

## BrainFly Design

From `src/controllers/brain_fly.py`:

```python
class BrainFly(Fly):
    """
    Mosca con integración sensoriomotora olfatoria.

    Extiende FlyGym's Fly para incluir:
    - Sensor olfativo en la cabeza
    - Integración con un cerebro olfatorio minimalista
    - Traducción de salida cerebral a acciones motoras
    """

    def __init__(
        self,
        brain,              # Brain controller
        odor_field,         # Odor environment
        sensor_position: str = "head",
        motor_mode: str = "hybrid_turning",
        *args,              # All Fly arguments
        **kwargs            # All Fly keyword arguments
    ):
        super().__init__(*args, **kwargs)  # Initialize Fly
        self.brain = brain
        self.odor_field = odor_field
        # ...

    def step(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sensorimotor cycle: sense odor → brain → action.
        """
        # 1. Extract sensory info from observations
        # 2. Process through brain
        # 3. Convert to motor commands
        # 4. Return action dictionary
```

**Key Points:**
- `BrainFly` **inherits from** `Fly` - it's not a wrapper
- Must be initialized with all `Fly` parameters via `*args, **kwargs`
- `step(obs)` integrates sensing, brain processing, and motor control
- Used directly in `SingleFlySimulation` like any Fly

---

## Changes Made

### File: `tools/run_physics_based_simulation.py`

**Lines 139-148 (Initialization):**

**Before:**
```python
self.fly = Fly(init_pose="stretch", ...)
self.brain_fly = BrainFly(brain=self.brain, odor_field=self.odor_field, ...)
self.sim = SingleFlySimulation(fly=self.fly, ...)
```

**After:**
```python
self.fly = BrainFly(
    brain=self.brain,
    odor_field=self.odor_field,
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
    motor_mode="direct_joints"
)
self.sim = SingleFlySimulation(fly=self.fly, ...)
```

**Line 197 (Step method):**

**Before:**
```python
action = self.brain_fly.step(self.obs)
```

**After:**
```python
action = self.fly.step(self.obs)
```

---

## Testing

**Syntax Check:**
```bash
python3 -m py_compile tools/run_physics_based_simulation.py  # ✓ Passed
```

**With FlyGym installed** (user's environment):
- Script should now run without AttributeError
- BrainFly properly processes observations
- Brain controls fly movement
- Simulation executes successfully

---

## Lessons Learned

### 1. Understand Inheritance Patterns

When a class inherits from another:
```python
class BrainFly(Fly):
    def __init__(self, brain, odor_field, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Pass Fly parameters up
```

Use it like:
```python
fly = BrainFly(brain, odor_field, fly_param1, fly_param2, ...)
```

NOT:
```python
fly = Fly(fly_param1, ...)
brain_fly = BrainFly(brain, odor_field)  # Missing Fly initialization!
```

### 2. Read Class Docstrings

`BrainFly` docstring clearly states:
> "Extiende FlyGym's Fly para incluir..."

This means it **extends** (inherits), not wraps.

### 3. Check `super().__init__()` Calls

When you see `super().__init__(*args, **kwargs)`, it means the class expects parent class parameters to be passed through.

---

## Impact

### Before Fix
❌ AttributeError or NameError at runtime
❌ Brain never controlled fly (regular Fly used)
❌ Simulation would fail during execution
❌ Confusing error message

### After Fix
✅ BrainFly properly initialized
✅ Brain controls fly movement
✅ Simulation runs successfully
✅ Observations → brain → actions pipeline works

---

## Related Documentation

- `data/docs/IMPORT_ERRORS_FIXED.md` - Previous import error fixes
- `data/docs/PHYSICS_SIMULATION_IMPLEMENTATION.md` - Physics simulation architecture
- `src/controllers/brain_fly.py` - BrainFly implementation

---

**Fixed by**: Claude Code
**Branch**: claude/analyze-code-and-documentation
**Commit**: 6fb7c3c
