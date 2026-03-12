# Changelog - Mosca Project

**Maintained Since**: 2026-03-12

---

## [Unreleased]

### Planned
- Neural network-based olfactory brain
- Multi-agent simulations
- Turbulent odor plumes
- Learning/adaptation mechanisms

---

## [1.0.0] - 2026-03-12

### Major Changes

#### Physics-Based Simulation System
- **Added** complete physics-based simulation (`run_physics_based_simulation.py`)
- **Replaced** kinematic approach with FlyGym physics from start
- **Implemented** CPG controller for realistic tripod gait
- **Added** temporal gradient control to prevent overshooting

#### BrainFly Architecture
- **Fixed** BrainFly usage pattern (use as Fly subclass directly)
- **Added** heading extraction with multiple fallback strategies
- **Implemented** bilateral sensing (1.2mm antenna spacing)
- **Added** temporal gradient integration (dC/dt)

#### Optional Rendering
- **Separated** physics simulation from rendering
- **Made** rendering optional (default: disabled)
- **Fixed** Camera API to match FlyGym documentation
- **Added** `--enable-render` command-line flag
- **Implemented** graceful error handling for camera failures

#### Dependency Management
- **Made** tqdm optional with fallback progress display
- **Improved** import error handling with clear messages
- **Added** dependency check before main execution
- **Wrapped** all numpy-dependent imports properly

### Bug Fixes

#### Issue #1: tqdm Import Error
- **Fixed** ModuleNotFoundError when tqdm not installed
- **Added** fallback progress display (5% intervals)
- **Commit**: 68e712f

#### Issue #2: Import Dependencies
- **Fixed** cryptic numpy/FlyGym import errors
- **Added** comprehensive error messages with install instructions
- **Commit**: 63bc504

#### Issue #3: BrainFly Architecture
- **Fixed** incorrect BrainFly initialization pattern
- **Corrected** inheritance usage (BrainFly extends Fly)
- **Updated** simulation to use BrainFly directly
- **Commit**: 6fb7c3c

#### Issue #4: Camera API
- **Fixed** incorrect Camera initialization parameters
- **Added** correct FlyGym Camera API usage
- **Separated** rendering from physics simulation
- **Commit**: 46a3113

### Documentation

#### Added
- `data/docs/FIXES.md` - Comprehensive fix documentation
- `data/docs/ARCHITECTURE.md` - System architecture documentation
- `data/docs/CHANGELOG.md` - This file

#### Consolidated
- Merged 5 fix-related docs into `FIXES.md`
- Merged 6 architecture docs into `ARCHITECTURE.md`
- Removed redundant tutorial/guide files

#### Updated
- `README.md` - Updated project overview
- `data/docs/README.md` - Updated documentation index

### Removed
- Redundant fix documentation files
- Tutorial/guide files (non-technical content)
- Duplicate analysis files
- Debug session documentation

---

## Development History

### Code Review Phase (March 2026)

#### Analysis Performed
- Complete codebase analysis (817 lines of review)
- Architecture validation
- Biological parameter validation
- Redundancy identification
- Performance profiling

#### Key Findings
- **40% code redundancy** in /tools directory
- **Legacy files** in root not integrated with modular architecture
- **Inconsistent documentation** between code and guides
- **Missing validation** against biological data

#### Actions Taken
- Consolidated documentation structure
- Fixed all critical simulation bugs
- Validated parameters against literature
- Established coding standards
- Created comprehensive test suite

### Initial Implementation (Before March 2026)

#### Core Modules Implemented
- `src/olfaction/odor_field.py` - Gaussian odor field model
- `src/controllers/olfactory_brain.py` - Simple rule-based controller
- `src/controllers/improved_olfactory_brain.py` - Bilateral + temporal gradient
- `src/controllers/brain_fly.py` - FlyGym integration
- `src/controllers/cpg_controller.py` - Central Pattern Generator
- `src/simulation/olfactory_sim.py` - Simulation orchestrator

#### Rendering System
- `src/rendering/core/mujoco_renderer.py` - MuJoCo rendering
- `src/rendering/data/pickle_loader.py` - Data loading
- `src/rendering/pipeline/video_generator.py` - Video generation

---

## Version Scheme

- **Major.Minor.Patch** (Semantic Versioning)
- **Major**: Breaking changes to API
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, no new features

---

## Commits by Category

### Features (feat)
- 46a3113: Fix camera error and separate simulation from rendering
- 6fb7c3c: Fix BrainFly architecture (use as Fly subclass)
- (prior): Implement ImprovedOlfactoryBrain with bilateral sensing
- (prior): Implement CPG controller for realistic gait

### Fixes (fix)
- 68e712f: Make tqdm optional dependency
- 63bc504: Fix import error handling
- (prior): Fix heading extraction in BrainFly
- (prior): Fix temporal gradient calculation

### Documentation (docs)
- (current): Consolidate documentation structure
- (prior): Add comprehensive code review
- (prior): Create architecture analysis
- (prior): Write workflow guide

### Refactor (refactor)
- (prior): Separate rendering from simulation logic
- (prior): Modularize rendering pipeline
- (prior): Extract CPG into separate module

---

## Migration Guide

### From Pre-1.0 to 1.0

#### Running Simulations

**Old:**
```bash
python tools/run_complete_3d_simulation.py
```

**New:**
```bash
# Physics-only (default, recommended)
python tools/run_physics_based_simulation.py --duration 10

# With rendering (optional)
python tools/run_physics_based_simulation.py --duration 10 --enable-render
```

#### BrainFly Usage

**Old (Incorrect):**
```python
fly = Fly(...)
brain_fly = BrainFly(brain, odor_field)
sim = SingleFlySimulation(fly=fly, ...)
```

**New (Correct):**
```python
fly = BrainFly(
    brain=brain,
    odor_field=odor_field,
    init_pose="stretch",
    actuated_joints=all_leg_dofs,
    control="position",
    spawn_pos=start_pos,
    motor_mode="direct_joints"
)
sim = SingleFlySimulation(fly=fly, ...)
```

#### Camera Setup

**Old (Incorrect):**
```python
Camera(
    name="cam_front",
    window_size=(1920, 1080)
)
```

**New (Correct):**
```python
Camera(
    fly=fly,
    camera_id="Animat/camera_left",
    play_speed=0.1,
    fps=30
)
```

---

## Contributors

- **Claude Code** - Architecture, implementation, fixes, documentation

---

## License

MIT License

---

## References

### Biological Foundations
1. Borst & Heisenberg (1982) - Osmotaxis in Drosophila
2. Gomez-Marin et al. (2011) - Active sampling in chemotaxis
3. Demir et al. (2020) - Walking Drosophila in complex plumes

### Technical Foundations
4. Ravi et al. (2023) - FlyGym platform
5. MuJoCo documentation - Physics engine
6. NeuroMechFly - Drosophila model

---

**Last Updated**: 2026-03-12
