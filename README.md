# Mosca - Olfactory Navigation in Drosophila

Physics-based simulation of chemotactic navigation in *Drosophila melanogaster* using FlyGym.

**Version**: 1.0.0
**Last Updated**: 2026-03-12

---

## Quick Start

### Installation

```bash
# Required dependencies
pip install flygym numpy

# Optional (for progress bars and video)
pip install tqdm opencv-python
```

### Run Simulation

```bash
# Physics-only simulation (recommended)
python tools/run_physics_based_simulation.py --duration 10 --seed 42

# With video rendering (optional, slower)
python tools/run_physics_based_simulation.py --duration 10 --enable-render
```

### Output

Results saved to `outputs/simulations/physics_3d/{TIMESTAMP}/`:
- `simulation_data.pkl` - Trajectory, odor concentrations, actions
- `simulation_video.mp4` - Video (if rendering enabled)
- `metadata.json` - Simulation parameters

---

## Recent Updates (2026-03-12)

### Critical Simulation Fixes

Three fixes were implemented to resolve locomotion issues in physics-based simulations:

1. **Brain Sensitivity**: Increased `temporal_gradient_gain` from 10.0 to 50.0
2. **CPG Support**: Increased baseline leg amplitude from 0.5 to 0.7
3. **Femur Extension**: Adjusted femur offset from -0.8 to -0.5 rad

**Results**: 52x improvement in forward action, stable body height, proper ground clearance.

**Documentation**:
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - Overview of fixes and results
- **[CHECKLIST_VERIFICATION.md](CHECKLIST_VERIFICATION.md)** - Verification steps
- **[outputs/tests/README.md](outputs/tests/README.md)** - Complete documentation index

**Verify Your Installation**:
```bash
# Check fixes are applied
grep "temporal_gradient_gain=50.0" tools/run_physics_based_simulation.py
grep "amplitude = 0.7" src/controllers/cpg_controller.py

# Run verification simulation
python tools/run_physics_based_simulation.py --duration 5
```

**Expected Results**:
- Forward mean > 0.02 (vs 0.00085 baseline)
- Z-axis stable > 1.5mm (no sinking)
- Distance > 50mm in 5 seconds

For troubleshooting, see [CHECKLIST_VERIFICATION.md](CHECKLIST_VERIFICATION.md).

---

## System Architecture

```
Sensory → Cognitive → Motor → Physical
  ↓         ↓          ↓        ↓
OdorField → Brain → BrainFly → FlyGym
```

**Key Components:**
- **OdorField**: Gaussian 3D odor concentration field
- **ImprovedOlfactoryBrain**: Bilateral sensing + temporal gradient control
- **BrainFly**: Integration with FlyGym physics (42 DoF)
- **CPG Controller**: Realistic tripod gait generation

---

## Core Features

### Biologically Realistic
- ✅ Bilateral antenna sensing (1.2mm spacing)
- ✅ Temporal gradient integration (dC/dt)
- ✅ Realistic walking gait (10 Hz tripod pattern)
- ✅ Validated parameters from literature

### Modular Architecture
- ✅ Separate sensing, cognition, motor control
- ✅ Easy to swap components
- ✅ Unit testable modules

### Physics-Based
- ✅ FlyGym/MuJoCo physics engine
- ✅ 42 degrees of freedom (6 legs × 7 DoF)
- ✅ Realistic forces and contacts
- ✅ 0.1ms physics timestep

### Rendering Optional
- ✅ Fast physics-only mode (default)
- ✅ Optional video rendering
- ✅ Graceful error handling
- ✅ Headless operation

---

## Project Structure

```
Mosca/
├── src/                              # Core modules
│   ├── olfaction/                   # Odor field model
│   ├── controllers/                 # Brain controllers
│   │   ├── improved_olfactory_brain.py  # ⭐ Current
│   │   ├── brain_fly.py             # FlyGym integration
│   │   └── cpg_controller.py        # Gait generation
│   ├── simulation/                  # Simulation orchestration
│   └── rendering/                   # Video rendering
│
├── tools/                            # Simulation scripts
│   ├── run_physics_based_simulation.py  # ⭐ Main script
│   ├── validate_simulation.py       # Validation suite
│   └── diagnose_*.py                # Diagnostic tools
│
├── data/
│   └── docs/                        # Technical documentation
│       ├── ARCHITECTURE.md          # System architecture
│       ├── FIXES.md                 # Bug fixes & solutions
│       ├── CHANGELOG.md             # Version history
│       └── README.md                # Dev standards
│
└── outputs/                          # Simulation results
    └── simulations/physics_3d/      # Timestamped outputs
```

---

## Biological Background

### Olfactory System

**Sensing:**
- 2 antennae with ~1,200 sensilla each
- Detection threshold: ~100-200 molecules
- Response time: 50-100 ms

**Neural Processing:**
```
Antennae (ORNs)
    ↓
Antennal Lobe (50+ glomeruli)
    ↓
Mushroom Body + Lateral Horn (integration)
    ↓
Central Complex (decisions)
    ↓
Motor output (descending neurons)
```

### Motor System

**Anatomy:**
- 6 legs (3 pairs: front, middle, hind)
- 7 joints per leg = 42 total degrees of freedom
- Tripod gait: alternating triplets (LF-RM-LH vs RF-LM-RH)

**Gait Parameters:**
- Frequency: 8-12 Hz
- Walking speed: 10 mm/s (typical)
- Turn rate: 200 °/s (typical)

### Chemotaxis Behaviors

1. **Gradient Climbing**: Follow increasing concentration
2. **Bilateral Comparison**: Turn toward higher concentration antenna
3. **Casting**: Search behavior when odor lost
4. **Surge**: Direct approach when odor detected

---

## Parameters

### Default Simulation Parameters

```python
# Odor field
odor_source = (50.0, 50.0, 5.0)  # mm
odor_sigma = 8.0                   # mm (plume width)
odor_amplitude = 100.0             # arbitrary units

# Initial conditions
start_pos = (35.0, 35.0, 3.0)     # mm
sim_duration = 5.0                 # seconds

# Physics
timestep = 1e-4                    # 0.1 ms
render_fps = 30                    # if rendering enabled

# Brain parameters
bilateral_distance = 1.2           # mm (antenna spacing)
forward_scale = 1.0
turn_scale = 0.8
threshold = 0.01
temporal_gradient_gain = 50.0      # Updated 2026-03-12 (was 10.0)
```

### Validated Against Literature

| Parameter | Value | Reference |
|-----------|-------|-----------|
| Antenna spacing | 1.2 mm | Anatomical data |
| Walking speed | 10 mm/s | Gomez-Marin et al. 2011 |
| Turn rate | 200 °/s | Gomez-Marin et al. 2011 |
| CPG frequency | 10 Hz | Stride frequency data |
| Detection threshold | 0.01 | Odor sensitivity studies |

---

## Documentation

**Technical Documentation** (in `data/docs/`):
- **[README.md](data/docs/README.md)** - Development standards and project rules
- **[ARCHITECTURE.md](data/docs/ARCHITECTURE.md)** - System design and components
- **[FIXES.md](data/docs/FIXES.md)** - Bug fixes and solutions
- **[CHANGELOG.md](data/docs/CHANGELOG.md)** - Version history and changes

**For Developers:**
1. Read `data/docs/README.md` for project standards
2. Read `ARCHITECTURE.md` for system overview
3. Read `FIXES.md` for common issues and solutions
4. Check `CHANGELOG.md` for recent changes

---

## References

### Scientific Publications

1. **Borst & Heisenberg** (1982). Osmotaxis in *Drosophila melanogaster*. *J Comp Physiol A* 147, 479-484.

2. **Gomez-Marin et al.** (2011). Active sampling and decision making in *Drosophila* chemotaxis. *Nat Commun* 2, 441.

3. **Demir et al.** (2020). Walking *Drosophila* navigate complex plumes using stochastic decisions biased by odor encounters. *Curr Biol* 30(2), 164-171.

4. **Ravi et al.** (2023). FlyGym: An Open-Source Physics-Based Neurorobotics Platform. *Nat Commun*.

### Technical References

- **FlyGym Documentation**: https://github.com/NeLy-EPFL/flygym
- **MuJoCo**: https://mujoco.org/
- **NeuroMechFly**: Neuromechanical model of *Drosophila*

---

## Contributing

Contributions welcome! Please:
1. Follow project standards in `data/docs/README.md`
2. Add tests for new features
3. Update documentation
4. Reference biological literature where applicable

---

## License

MIT License

---

## Contact

NeuroMechFly Sim Project
GitHub: https://github.com/rougnull/Mosca

---

**Last Updated**: 2026-03-12
