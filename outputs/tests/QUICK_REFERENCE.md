# Quick Reference: Running Simulations After CPG Fix

## Verification Checklist

Before running your simulation, verify the fix is applied:

```bash
# 1. Check BrainFly accepts timestep parameter
grep -n "timestep: float" src/controllers/brain_fly.py
# Should show line ~53: timestep: float = 1e-4

# 2. Check CPG uses self.timestep
grep -n "self.timestep" src/controllers/brain_fly.py
# Should show line ~382: timestep=self.timestep

# 3. Run test suite
python tools/test_all_components.py
# Should pass all 3 tests and save data to outputs/tests/
```

## Running Simulations

### Option 1: Test Suite (Quick Verification)
```bash
python tools/test_all_components.py
```
**Duration:** ~1 minute
**Output:**
- Console output with test results
- Data file: `outputs/tests/physics_test_<timestamp>.pkl`

**Expected Results:**
```
✅ PASSED: Brain generates appropriate turn signals
✅ PASSED: Observation extraction working correctly
✅ PASSED: All available tests passed

Turn signals: min=-0.406, max=-0.088
Distance traveled: ~0.70mm
Min Z: 1.78mm (NO ground penetration)
```

### Option 2: Full Physics Simulation
```bash
python tools/run_physics_based_simulation.py --duration 5
```
**Duration:** ~5-10 minutes (depending on hardware)
**Output:**
- Console output with progress
- Data file: `outputs/simulations/physics_3d/<timestamp>/simulation_data.pkl`
- Video file: `outputs/simulations/physics_3d/<timestamp>/simulation_video.mp4` (if --enable-render)

**Expected Behavior:**
- Stable fly posture throughout
- No ground penetration (Z > 0 always)
- Controlled turning toward odor source
- Forward movement when concentration increases
- Console shows: `[BrainFly] Initialized CPG controller with timestep=0.0001`

### Option 3: Individual Component Test
```bash
# Test just the physics integration (50 steps)
python tools/test_short_simulation.py
```
**Duration:** ~10 seconds
**Output:** Console output with 50-step simulation analysis

## Analyzing Results

### Load Test Data
```python
import pickle
import numpy as np

# Load test data
with open('outputs/tests/physics_test_<timestamp>.pkl', 'rb') as f:
    data = pickle.load(f)

# Check configuration
print("Configuration:", data['configuration'])
print("  Timestep:", data['configuration']['timestep'])  # Should be 1e-4

# Check statistics
stats = data['statistics']
print("\nStatistics:")
print(f"  Turn range: [{stats['turn_min']:.3f}, {stats['turn_max']:.3f}]")
print(f"  Distance: {stats['distance_traveled']:.3f} mm")
print(f"  Z range: [{stats['z_min']:.3f}, {stats['z_max']:.3f}] mm")

# Check for issues
issues = data['issues']
print("\nIssues:")
print(f"  Ground penetration: {issues['ground_penetration']}")  # Should be False
print(f"  Turn signal zero: {issues['turn_signal_zero']}")      # Should be False
print(f"  Minimal movement: {issues['minimal_movement']}")      # Should be False
```

### Visualize Trajectory
```python
import matplotlib.pyplot as plt

positions = data['positions']
headings = data['headings']

# Plot XY trajectory
plt.figure(figsize=(10, 5))

plt.subplot(1, 2, 1)
plt.plot(positions[:, 0], positions[:, 1], 'b-', linewidth=2)
plt.scatter(positions[0, 0], positions[0, 1], c='green', s=100, label='Start', zorder=5)
plt.scatter(positions[-1, 0], positions[-1, 1], c='red', s=100, label='End', zorder=5)
plt.scatter(50, 50, c='orange', s=200, marker='*', label='Odor Source', zorder=5)
plt.xlabel('X (mm)')
plt.ylabel('Y (mm)')
plt.title('XY Trajectory')
plt.legend()
plt.grid(True, alpha=0.3)
plt.axis('equal')

plt.subplot(1, 2, 2)
plt.plot(positions[:, 2], 'b-', linewidth=2)
plt.axhline(y=0, color='r', linestyle='--', label='Ground Level')
plt.xlabel('Step')
plt.ylabel('Z (mm)')
plt.title('Vertical Position')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/tests/trajectory_analysis.png', dpi=150)
plt.show()
```

### Compare Before/After Fix

If you have simulation data from before the fix (e.g., `2026-03-12_20_53`):

```python
# This is hypothetical - user would need to analyze their old data
import pickle

# Before fix (if available)
# with open('outputs/simulations/physics_3d/2026-03-12_20_53/simulation_data.pkl', 'rb') as f:
#     old_data = pickle.load(f)

# After fix
with open('outputs/tests/physics_test_<timestamp>.pkl', 'rb') as f:
    new_data = pickle.load(f)

# Compare turn signals
# old_turns = old_data['brain_actions'][:, 1]  # Would show ~1.5e-15
new_turns = new_data['brain_actions'][:, 1]   # Shows -0.4 to -0.09

print("Turn Signals Comparison:")
# print(f"  Before: {np.mean(np.abs(old_turns)):.2e} (essentially zero)")
print(f"  After:  {np.mean(np.abs(new_turns)):.3f} (appropriate)")

# Compare Z positions
# old_z = old_data['positions'][:, 2]  # Would show Z < 0
new_z = new_data['positions'][:, 2]   # Shows Z > 0

print("\nZ Position Comparison:")
# print(f"  Before: min={np.min(old_z):.3f} mm (ground penetration!)")
print(f"  After:  min={np.min(new_z):.3f} mm (stable)")
```

## Troubleshooting

### Issue: "CPG controller timestep=0.01" in output
**Problem:** Old code is being used
**Solution:**
```bash
git pull origin claude/analyze-code-and-documentation
python tools/test_all_components.py  # Verify fix
```

### Issue: Still seeing ground penetration
**Check:**
1. Console shows correct timestep: `[BrainFly] Initialized CPG controller with timestep=0.0001`
2. If not, check that you're calling BrainFly with `timestep=timestep` parameter
3. Run test suite to verify: `python tools/test_all_components.py`

### Issue: Turn signals still zero
**Check:**
1. Observation extraction working: Run test 2 individually
2. Brain generating signals: Run test 1 individually
3. If both pass but physics fails, check timestep parameter

### Issue: Simulation crashes or hangs
**Check:**
1. FlyGym and dependencies installed: `pip install flygym numpy`
2. Sufficient memory available (FlyGym physics needs ~2GB)
3. Try shorter duration first: `--duration 1`

## Performance Notes

- **Test suite:** ~1 minute (200 steps)
- **1 second simulation:** ~1-2 minutes
- **5 second simulation:** ~5-10 minutes
- **With rendering:** 2-3x slower

Memory usage:
- Test suite: ~500MB
- 5s simulation: ~2GB
- With rendering: ~4GB

## Next Steps

After verifying the fix works:

1. **Run longer simulations** to confirm stability over time
2. **Adjust CPG parameters** if needed (frequency, amplitude)
3. **Enable rendering** to visualize behavior: `--enable-render`
4. **Analyze saved data** to tune brain parameters

## Contact

If issues persist after applying this fix:
1. Check outputs/tests/ANALYSIS_CPG_TIMESTEP_FIX.md for technical details
2. Run diagnostic tests: `python tools/test_all_components.py`
3. Save and share test data from outputs/tests/
