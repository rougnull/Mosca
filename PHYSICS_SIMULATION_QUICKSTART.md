# Quick Start: Physics-Based Simulation

This guide shows how to run the new physics-based simulation that fixes the 3D rendering issues.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install FlyGym (required)
pip install flygym

# Install video support (optional)
pip install opencv-python
```

### 2. Run Simulation

```bash
# Default: 5-second simulation with video
python tools/run_physics_based_simulation.py

# Longer simulation (10 seconds)
python tools/run_physics_based_simulation.py --duration 10

# Fast test (no video recording)
python tools/run_physics_based_simulation.py --no-video
```

### 3. View Results

Results are saved in `outputs/simulations/physics_3d/{timestamp}/`:
- `simulation_video.mp4` - Rendered video of fly navigation
- `simulation_data.pkl` - Complete trajectory data

## 🆚 What's Different?

### Old (Kinematic) vs New (Physics)

| Feature | Old `run_complete_3d_simulation.py` | New `run_physics_based_simulation.py` |
|---------|-------------------------------------|---------------------------------------|
| **Physics Engine** | ❌ None (manual integration) | ✅ FlyGym/MuJoCo |
| **Ground Contact** | ❌ No (Z constant) | ✅ Yes (collision detection) |
| **Body Balance** | ❌ No (rotates 180°) | ✅ Yes (stays upright) |
| **Joint Angles** | ⚠️ Synthetic (sine waves) | ✅ CPG-generated (realistic) |
| **Sinking** | ❌ Yes (passes through ground) | ✅ No (proper support) |
| **Movement** | ⚠️ Appears ~1 fps | ✅ Smooth at 30 fps |

## 📊 Expected Behavior

With the physics-based simulation, you should see:

✅ **Smooth walking motion**
- Natural tripod gait coordination
- Alternating leg groups (LF+RM+LH vs RF+LM+RH)
- Realistic leg lifting and placement

✅ **Stable body orientation**
- Body stays parallel to ground
- No rotation or tilting
- Proper balance maintained

✅ **Ground contact**
- Legs always touching ground during stance
- No sinking or floating
- Realistic Z-position variations

✅ **Chemotaxis behavior**
- Fly moves toward odor source
- Bilateral sensing (left vs right comparison)
- Forward movement increases with concentration gradient

## 🔧 Troubleshooting

### "FlyGym not available"

```bash
pip install flygym
```

If installation fails, check Python version (requires 3.8+).

### Simulation runs but no video

Install OpenCV:
```bash
pip install opencv-python
```

Or run without video:
```bash
python tools/run_physics_based_simulation.py --no-video
```

### Fly movement seems slow

This is expected! Physics simulation is computationally intensive:
- **Kinematic**: ~1 second for 1500 steps
- **Physics**: ~30 seconds for 1500 steps

The final video plays at normal speed (30 fps).

### Video shows fly sinking slowly

This might indicate joint angle issues. Check:
1. Femur angle range (should be -1.5 to -0.2, naturally bent)
2. Tibia angle range (should be 0.3 to 1.8, extended)
3. CPG base frequency (try reducing from 2.0 to 1.5 Hz)

Report this as an issue if it persists!

## 📖 How It Works

### Architecture

```
ImprovedOlfactoryBrain
  ↓ [forward, turn]
CPG Controller (cpg_controller.py)
  ↓ 42 joint angles (tripod gait)
FlyGym Physics Engine
  ↓ Forces, collisions, dynamics
Realistic Movement
  ↓
Video Recording
```

### Key Components

1. **CPG Controller** (`src/controllers/cpg_controller.py`)
   - Converts high-level commands [forward, turn] to 42 joint angles
   - Implements tripod gait (biologically realistic)
   - Smooth transitions and adaptive parameters

2. **Enhanced BrainFly** (`src/controllers/brain_fly.py`)
   - Integrates CPG controller
   - Extracts heading from FlyGym observations
   - Passes data to ImprovedOlfactoryBrain

3. **Physics Simulation** (`tools/run_physics_based_simulation.py`)
   - Uses FlyGym from the start (no kinematic preprocessing)
   - Direct rendering from physics simulation
   - Proper ground contact and body dynamics

## 📚 Documentation

- **`PHYSICS_SIMULATION_IMPLEMENTATION.md`** - Complete technical documentation
- **`DIAGNOSTIC_SIMULATION_ISSUES.md`** - Analysis of problems with old approach
- **`DIAGNOSTIC_SUMMARY.md`** - Executive summary of root cause

## 🆘 Getting Help

If you encounter issues:

1. Check that FlyGym is installed: `python -c "import flygym; print(flygym.__version__)"`
2. Try a short simulation first: `python tools/run_physics_based_simulation.py --duration 2`
3. Run without video: `python tools/run_physics_based_simulation.py --no-video`
4. Check the output logs for error messages

## 🎯 Next Steps

Once you verify the simulation works correctly:

1. **Extend duration**: Try 10-15 second simulations
2. **Vary parameters**: Experiment with odor sigma, amplitude, starting position
3. **Analyze data**: Load the PKL file and plot trajectories
4. **Compare behaviors**: Test different brain parameters

## 💡 Tips

- **Start small**: Test with 2-3 second simulations first
- **Use --no-video**: Much faster for testing/debugging
- **Check the PKL**: Even without video, you can analyze trajectory data
- **Be patient**: Physics simulation is slow but accurate

---

**Questions?** Check the full documentation in `data/docs/PHYSICS_SIMULATION_IMPLEMENTATION.md`
