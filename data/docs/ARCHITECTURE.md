# Architecture - Mosca Project

**Last Updated**: 2026-03-12

---

## Overview

Mosca implements a modular sensorimotor architecture for simulating olfactory navigation in *Drosophila melanogaster* using FlyGym physics engine.

---

## System Architecture

### High-Level Pipeline

```
┌────────────────────────────────────────────────────┐
│          FlyGym Physics Simulation                 │
│  (MuJoCo, 42 DoF, 10 kHz timestep, obs dict)      │
└─────────────────────┬────────────────────────────┘
                      │ obs: {position, velocity, forces, ...}
                      ↓
        ┌─────────────────────────────┐
        │    BrainFly.step(obs)       │
        │  (Sensorimotor Integration) │
        └────┬────────────────────┬───┘
             │                    │
             ↓                    ↓
    ┌──────────────────┐   ┌──────────────────────┐
    │   OdorField      │   │  OlfactoryBrain      │
    │                  │   │                      │
    │ concentration_   │   │ step(conc, pos,      │
    │   at(pos) →      │──→│   heading) →         │
    │   float          │   │ [forward, turn]      │
    └──────────────────┘   └──────────────────────┘
             ↑                     │
             └─────────────────────┼──────────────────┐
                                   │                  │
                      ┌────────────┘                  │
                      ↓                               │
        ┌─────────────────────────────┐              │
        │  Motor Conversion (CPG)     │◄─────────────┘
        │  [f, t] → 42-dim action     │
        └────────────┬────────────────┘
                     │
                     ↓
        action = {"joints": {joint_actions}}
                     │
                     ↓
        ┌────────────────────────────────────┐
        │ Simulation.step(action)            │
        │ → new obs, forces, contacts, etc.  │
        └────────────────────────────────────┘
```

### Abstraction Levels

| Level | Component | Input | Output | Role |
|-------|-----------|-------|--------|------|
| **Sensorial** | OdorField | 3D position | scalar conc | Detect chemicals in field |
| **Cognitive** | OlfactoryBrain | conc, position, heading | [f, t] ∈ [-1,1] | Make decisions |
| **Motor** | BrainFly | [f, t] | 42-dim action | Translate to joint commands |
| **Physical** | Simulation | action dict | obs + forces | Calculate real dynamics |

---

## Core Components

### 1. OdorField (`src/olfaction/odor_field.py`)

**Purpose**: Model 3D concentration distribution

**Model**: Gaussian plume
```
C(x) = A × exp(-||x - s||² / (2σ²))
```

**API:**
```python
class OdorField:
    def __init__(self, sources: tuple, sigma: float, amplitude: float)
    def concentration_at(pos: np.ndarray) -> float
    def gradient_at(pos: np.ndarray) -> np.ndarray
```

**Features:**
- Multiple sources (sum of gaussians)
- Vectorized evaluation
- Gradient calculation via finite differences

### 2. ImprovedOlfactoryBrain (`src/controllers/improved_olfactory_brain.py`)

**Purpose**: Convert olfactory input → motor commands

**Input:**
- `odor_concentration` ∈ [0, 1]
- `position` (x, y, z) in mm
- `heading_radians` ∈ [0, 2π)

**Output:**
- `[forward, turn]` ∈ [-1, 1]²

**Strategy: Bilateral Sensing + Temporal Gradient**

```python
# Bilateral sensing (like real antennae)
left_pos = position + rotate(-bilateral_distance/2, heading)
right_pos = position + rotate(+bilateral_distance/2, heading)
conc_left = odor_field.concentration_at(left_pos)
conc_right = odor_field.concentration_at(right_pos)

# Turn toward higher concentration
turn = turn_scale × (conc_right - conc_left)

# Forward based on temporal gradient (prevents overshooting)
d_conc_dt = current_conc - previous_conc
forward = forward_scale × tanh(temporal_gradient_gain × d_conc_dt)
```

**Key Parameters:**
- `bilateral_distance` = 1.2 mm (real antenna spacing)
- `forward_scale` = 1.0
- `turn_scale` = 0.8
- `threshold` = 0.01
- `temporal_gradient_gain` = 10.0

### 3. BrainFly (`src/controllers/brain_fly.py`)

**Purpose**: Integrate olfactory brain with FlyGym physics

**Class Hierarchy:**
```python
class BrainFly(flygym.Fly):
    """Fly with integrated olfactory brain"""
```

**Key Insight:** BrainFly IS a Fly, not a wrapper

**Pipeline per step:**
```
1. obs ← Simulation.step(previous_action)
2. head_pos ← extract_position(obs)
3. heading ← extract_heading(obs)
4. conc ← odor_field.concentration_at(head_pos)
5. [f, t] ← brain.step(conc, head_pos, heading)
6. action ← motor_conversion([f, t])  # [f, t] → 42 DoF
7. return action
```

**Motor Conversion Methods:**

1. **Hybrid (default)**: Uses CPG for realistic gait
2. **Direct mapping**: Simple gain matrix

**Heading Extraction Strategies:**
- Quaternion-based (primary)
- Euler angles (fallback)
- Velocity-based (if orientation unavailable)
- Last-known (backup)

### 4. CPG Controller (`src/controllers/cpg_controller.py`)

**Purpose**: Convert [forward, turn] → 42 joint angles with realistic gait

**Architecture:**
- 6 legs × 7 DoF = 42 joints
- Tripod gait pattern:
  - Group 1: LF + RM + LH (phase = 0)
  - Group 2: RF + LM + RH (phase = π)
- Phase-based oscillators

**Frequency:** 8-12 Hz (realistic fly walking)

**Modulation:**
- Forward speed → amplitude
- Turn command → leg frequency asymmetry

---

## Directory Structure

```
Mosca/
├── src/                                # Core modules
│   ├── olfaction/
│   │   └── odor_field.py              # Gaussian odor field
│   ├── controllers/
│   │   ├── olfactory_brain.py         # Legacy (simple binary/gradient)
│   │   ├── improved_olfactory_brain.py # ⭐ Current (bilateral + temporal)
│   │   ├── brain_fly.py               # FlyGym integration
│   │   └── cpg_controller.py          # Central Pattern Generator
│   ├── simulation/
│   │   └── olfactory_sim.py           # Simulation orchestrator
│   ├── rendering/
│   │   ├── data/                      # Data loading
│   │   ├── core/                      # MuJoCo rendering
│   │   └── pipeline/                  # Rendering orchestration
│   └── core/
│       ├── config.py                  # Configuration dataclasses
│       └── data.py                    # Data formatting
│
├── tools/                              # Simulation scripts
│   ├── run_physics_based_simulation.py # ⭐ Main physics simulation
│   ├── run_complete_3d_simulation.py   # Complete 3D pipeline
│   ├── validate_simulation.py          # Validation suite
│   ├── diagnose_*.py                   # Diagnostic tools
│   └── test_*.py                       # Unit tests
│
├── data/
│   ├── docs/                          # Technical documentation
│   ├── notebooks/                     # Jupyter notebooks
│   ├── debug/                         # Debug logs
│   └── inverse_kinematics/            # IK data
│
└── outputs/
    └── simulations/                   # Timestamped simulation results
        └── physics_3d/
            └── {YYYY-MM-DD_HH-MM}/
                ├── simulation_data.pkl
                ├── simulation_video.mp4
                └── metadata.json
```

---

## Key Design Decisions

### 1. Modular Sensorimotor Pipeline

**Rationale:**
- Separates sensing, cognition, motor control
- Each component can be tested independently
- Easy to swap implementations (e.g., neural network brain)

**Benefits:**
- Clear interfaces
- Unit testable
- Extensible

### 2. BrainFly as Fly Subclass

**Initial Mistake:** Creating separate Fly and BrainFly objects

**Correct Approach:** BrainFly extends Fly
```python
# BrainFly inherits all Fly functionality
self.fly = BrainFly(
    brain=self.brain,
    odor_field=self.odor_field,
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
    motor_mode="direct_joints"
)

# Use directly in simulation
self.sim = SingleFlySimulation(fly=self.fly, ...)
```

**Lesson:** Understand inheritance patterns in framework

### 3. Optional Rendering

**Problem:** Rendering was mandatory, causing failures

**Solution:** Separate physics from visualization
```python
# Default: physics-only (fast, robust)
sim = PhysicsBasedOlfactorySimulation(enable_rendering=False)

# Optional: with video
sim = PhysicsBasedOlfactorySimulation(enable_rendering=True)
```

**Benefits:**
- Faster iteration during development
- Robust to camera setup issues
- Headless operation for batch experiments

### 4. Bilateral Sensing

**Biological Reality:** *Drosophila* has two antennae

**Implementation:**
```python
bilateral_distance = 1.2  # mm (actual antenna spacing)
left_conc = odor_field.concentration_at(pos - offset)
right_conc = odor_field.concentration_at(pos + offset)
turn = turn_scale × (right_conc - left_conc)
```

**Impact:** More realistic chemotaxis behavior

### 5. Temporal Gradient

**Problem:** Spatial gradient alone causes overshooting

**Solution:** Use dC/dt for forward control
```python
d_conc_dt = current_conc - previous_conc
forward = forward_scale × tanh(gain × d_conc_dt)
```

**Benefits:**
- Prevents overshooting source
- More stable navigation
- Matches real fly behavior

---

## Performance Considerations

### Bottlenecks

1. **MuJoCo physics**: O(n²) for collision detection
2. **Rendering**: ~30 FPS, GPU-dependent
3. **OdorField**: O(num_sources) per evaluation

### Optimizations Applied

1. **Vectorized odor field**: NumPy broadcasting
2. **Optional rendering**: Skip when not needed
3. **Fixed timestep**: 0.1 ms (stable)
4. **Efficient CPG**: Precomputed phase tables

### Scalability

- **Multi-source**: Linear in number of sources
- **Multi-agent**: Linear in number of flies
- **Longer simulations**: Linear in duration

---

## Biological Validation

### Parameters Validated Against Literature

| Parameter | Value | Source |
|-----------|-------|--------|
| Antenna spacing | 1.2 mm | Anatomy measurements |
| Walking speed | 10 mm/s | Behavioral studies |
| Turn rate | 200 °/s | Gomez-Marin et al. 2011 |
| CPG frequency | 10 Hz | Stride frequency data |
| Detection threshold | 0.01 | Odor sensitivity studies |

### Behavioral Validation

✅ Chemotaxis toward source
✅ Casting behavior when odor lost
✅ Bilateral comparison (klinotaxis)
✅ Realistic gait patterns
✅ Speed modulation by odor strength

---

## Extension Points

### Easy Extensions

1. **Different brain controllers**: Inherit from `OlfactoryBrain`
2. **Different odor fields**: Modify `OdorField` equations
3. **Different arenas**: Use FlyGym arena classes
4. **Multiple flies**: Create multiple `BrainFly` instances

### Medium Extensions

1. **Neural network brain**: Replace rule-based controller
2. **Turbulent odor plumes**: Convolve with turbulence kernel
3. **Learning**: Add plasticity to brain
4. **Multi-modal sensing**: Add visual cues

### Advanced Extensions

1. **Connectome-based models**: Implement neural circuits
2. **Neuromodulation**: Add internal states
3. **Social interactions**: Multi-agent communication
4. **Evolution**: Genetic algorithm for parameter optimization

---

## Common Patterns

### Adding a New Brain Controller

```python
class MyBrain(OlfactoryBrain):
    def step(self, conc, position, heading):
        # Your algorithm here
        forward = ...
        turn = ...
        return np.array([forward, turn])
```

### Running a Simulation

```python
from tools.run_physics_based_simulation import PhysicsBasedOlfactorySimulation

sim = PhysicsBasedOlfactorySimulation(
    odor_source=(50.0, 50.0, 5.0),
    odor_sigma=8.0,
    odor_amplitude=100.0,
    start_pos=(35.0, 35.0, 3.0),
    sim_duration=10.0,
    enable_rendering=False  # Physics-only
)

success = sim.run(save_video=False)
output_dir = sim.save_data()
```

### Adding Diagnostics

```python
# In simulation loop
if step_idx % 1000 == 0:
    conc = odor_field.concentration_at(position)
    distance = np.linalg.norm(position - source)
    print(f"Step {step_idx}: conc={conc:.4f}, dist={distance:.1f}mm")
```

---

## Testing Strategy

### Unit Tests

Each module has embedded tests:
```bash
python src/olfaction/odor_field.py          # Test odor field
python src/controllers/olfactory_brain.py   # Test brain
python src/controllers/brain_fly.py         # Test integration
```

### Integration Tests

```bash
python tools/validate_simulation.py         # Full simulation test
python tools/diagnose_flygym_render.py      # Rendering test
```

### Validation Checklist

- [ ] OdorField: Gaussian profile correct
- [ ] OlfactoryBrain: Output in range [-1, 1]
- [ ] BrainFly: Integrates without errors
- [ ] Simulation: Fly moves toward source
- [ ] Rendering: Video generated (if enabled)

---

## Related Documentation

- `FIXES.md` - All bug fixes and solutions
- `CHANGELOG.md` - Version history
- `README.md` - Project overview and biological background
