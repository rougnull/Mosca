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
│       └── CHANGELOG.md             # Version history
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
temporal_gradient_gain = 10.0
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
- **[ARCHITECTURE.md](data/docs/ARCHITECTURE.md)** - System design and components
- **[FIXES.md](data/docs/FIXES.md)** - Bug fixes and solutions
- **[CHANGELOG.md](data/docs/CHANGELOG.md)** - Version history and changes

**For Developers:**
1. Read `ARCHITECTURE.md` for system overview
2. Read `FIXES.md` for common issues and solutions
3. Check `CHANGELOG.md` for recent changes

**For Users:**
1. Follow Quick Start above
2. Adjust parameters in simulation script
3. Analyze output data (see Output section)

---

## Usage Examples

### Basic Simulation

```python
from tools.run_physics_based_simulation import PhysicsBasedOlfactorySimulation

sim = PhysicsBasedOlfactorySimulation(
    odor_source=(50.0, 50.0, 5.0),
    odor_sigma=8.0,
    odor_amplitude=100.0,
    start_pos=(35.0, 35.0, 3.0),
    sim_duration=10.0,
    enable_rendering=False  # Fast physics-only mode
)

success = sim.run(save_video=False)
output_dir = sim.save_data()
print(f"Results saved to: {output_dir}")
```

### Custom Brain Controller

```python
from src.controllers.olfactory_brain import OlfactoryBrain
import numpy as np

class MyBrain(OlfactoryBrain):
    def step(self, concentration, position, heading):
        # Your custom control algorithm
        forward = min(concentration * 2.0, 1.0)
        turn = np.random.uniform(-0.1, 0.1)
        return np.array([forward, turn])

# Use in simulation
brain = MyBrain()
fly = BrainFly(brain=brain, odor_field=odor_field, ...)
```

### Batch Experiments

```bash
# Run multiple seeds
for seed in {1..10}; do
    python tools/run_physics_based_simulation.py --duration 20 --seed $seed
done

# Analyze results
python tools/analyze_experiments.py outputs/simulations/physics_3d/
```

---

## Testing

### Unit Tests

```bash
# Test individual modules
python src/olfaction/odor_field.py
python src/controllers/olfactory_brain.py
python src/controllers/brain_fly.py
```

### Integration Tests

```bash
# Full simulation validation
python tools/validate_simulation.py

# Rendering validation (if enabled)
python tools/diagnose_flygym_render.py
```

---

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Install required dependencies
pip install flygym numpy
```

**2. Camera Errors**
```bash
# Run without rendering (default)
python tools/run_physics_based_simulation.py --duration 10

# Rendering is optional - use --enable-render only if needed
```

**3. Simulation Fails**
```bash
# Enable verbose output
python tools/validate_simulation.py

# Check diagnostic tools
python tools/diagnose_flygym_render.py
```

See `data/docs/FIXES.md` for detailed solutions.

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
1. Follow existing code style
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
