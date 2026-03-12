# Quick Verification Checklist

Use this checklist to verify that all fixes are working correctly.

## Pre-Flight Check

- [ ] Repository is up to date (`git pull`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Previous simulation data backed up (optional)

## Step 1: Verify Code Changes

### Check Brain Sensitivity Fix
```bash
grep "temporal_gradient_gain=" tools/run_physics_based_simulation.py
```
**Expected:** Should show `temporal_gradient_gain=50.0` (not 10.0)

### Check CPG Amplitude Fix
```bash
grep "amplitude = " src/controllers/cpg_controller.py | head -1
```
**Expected:** Should show `amplitude = 0.7 + 0.3 * abs(forward)` (not 0.5 + 0.5)

### Check Femur Extension Fix
```bash
grep -A 1 "offset = -" src/controllers/cpg_controller.py | grep -A 1 "Femur"
```
**Expected:** Should show `offset = -0.5` in Femur section (not -0.8)

- [ ] All code changes verified ✅

## Step 2: Run New Simulation

```bash
python tools/run_physics_based_simulation.py --duration 5
```

- [ ] Simulation runs without errors ✅
- [ ] Output directory created in `outputs/simulations/physics_3d/` ✅

## Step 3: Check Critical Metrics

From the simulation output, verify:

### Forward Action
```
Brain Actions Statistics:
  Forward: mean = ?
```
- [ ] Forward mean > 0.02 (target: ~0.05) ✅
- [ ] Forward values vary significantly (not stuck at ~0) ✅

### Z-Axis Height
```
Position Statistics:
  Initial Z: ?
  Final Z: ?
  Mean Z: ?
  Min Z: ?
```
- [ ] Initial Z ≈ 1.8mm ✅
- [ ] Final Z > 1.5mm (ideally ≈ 2mm) ✅
- [ ] Final Z ≥ Initial Z (rising or stable, not sinking) ✅
- [ ] Min Z > 1.0mm ✅
- [ ] Steps with Z < 0.5mm: < 10% ✅

### Movement
```
Position Statistics:
  Distance traveled: ?
```
- [ ] Distance > 50mm (target: ~100mm) ✅
- [ ] Significant improvement from 7mm baseline ✅

### Concentration Response
```
Concentration Statistics:
  Mean dC/dt: ?
  Steps with |dC| > 0.01: ?
```
- [ ] Mean dC/dt > 1e-04 (higher than 5.8e-05 baseline) ✅
- [ ] Some steps with significant dC > 0.01 ✅

## Step 4: Visual Inspection (Optional)

If visualization is available:

- [ ] Fly maintains upright posture throughout ✅
- [ ] Legs exhibit tripod gait pattern ✅
- [ ] No ground penetration ✅
- [ ] Smooth locomotion (not jerky) ✅

## Results Comparison

| Metric | Old (21_11) | Target | Actual | Status |
|--------|-------------|--------|--------|--------|
| Forward mean | 0.00085 | > 0.02 | _____ | ⬜ |
| Z final | 0.263mm | > 1.5mm | _____ | ⬜ |
| Z trend | ↓ Sinking | Stable/↑ | _____ | ⬜ |
| Distance | 7.0mm | > 50mm | _____ | ⬜ |
| Min Z | 0.217mm | > 1.0mm | _____ | ⬜ |

## Troubleshooting

### ❌ Forward still low (< 0.02)

**Check:**
1. Is temporal_gradient_gain actually 50.0?
   ```bash
   grep "temporal_gradient_gain=" tools/run_physics_based_simulation.py
   ```

2. Is odor field configured correctly?
   ```bash
   grep "OdorPlume" tools/run_physics_based_simulation.py -A 5
   ```

3. Is fly starting in odor field?
   ```bash
   grep "start_pos" tools/run_physics_based_simulation.py
   ```

**If all correct but still low:**
- Try increasing to temporal_gradient_gain=75 or 100
- Check simulation output for error messages

### ❌ Z-axis still sinking

**Check:**
1. Is amplitude baseline 0.7?
   ```bash
   grep "amplitude = 0.7" src/controllers/cpg_controller.py
   ```

2. Is femur offset -0.5?
   ```bash
   grep "offset = -0.5" src/controllers/cpg_controller.py
   ```

**If all correct but still sinking:**
- Increase amplitude to 0.8: `amplitude = 0.8 + 0.2 * abs(forward)`
- Extend femur more: `offset = -0.4`
- Verify adhesion is enabled in simulation config

### ❌ Movement is erratic/unstable

**Possible fixes:**
- Reduce temporal_gradient_gain to 30-40 (may be overshooting)
- Use AdaptiveCPGController for smoother transitions
- Check turn values aren't causing excessive spinning

## Success Criteria

✅ **ALL of the following must be true:**

1. Forward action mean > 0.02
2. Z-axis final height > 1.5mm
3. Z-axis not declining over time
4. Distance traveled > 50mm
5. No persistent ground contact (Z < 0.5mm for < 10% of steps)

If all criteria met: **VERIFICATION COMPLETE** ✅

If any criteria failed: See troubleshooting section or review:
- `outputs/tests/VERIFICATION_GUIDE.md` (detailed guide)
- `outputs/tests/DIAGNOSTIC_REPORT_2026-03-12_21_11.md` (technical analysis)
- `outputs/tests/RESUMEN_CORRECCIONES.md` (Spanish summary)

## Report Template

If you need to report issues, provide:

```
**Simulation Details:**
- Date/Time: [timestamp from output directory]
- Duration: 5 seconds
- Steps: [from output]

**Metrics:**
- Forward mean: [value]
- Z initial: [value]
- Z final: [value]
- Z min: [value]
- Distance: [value]

**Issues:**
- [Describe what doesn't match expected results]

**Error Messages:**
- [Any errors or warnings from simulation]
```

---

**Quick Command Reference:**

```bash
# Run simulation
python tools/run_physics_based_simulation.py --duration 5

# Check latest output
ls -lt outputs/simulations/physics_3d/ | head -5

# Quick verification of fixes
grep "temporal_gradient_gain=" tools/run_physics_based_simulation.py
grep "amplitude = 0.7" src/controllers/cpg_controller.py
grep "offset = -0.5" src/controllers/cpg_controller.py
```
