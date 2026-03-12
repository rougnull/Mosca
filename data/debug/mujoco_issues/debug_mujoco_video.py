#!/usr/bin/env python3
"""
DEBUG: MuJoCo Video Generation Issue

PROBLEMA REPORTADO:
- El video generado es 2D (matplotlib) en lugar de 3D (MuJoCo)
- Expected: Video 3D real de la mosca moviéndose en 3D con cinemática propia
- Actual: Video 2D con gráficos de trayectoria XY del movimiento

CAUSA PROBABLE:
- FlyGym/MuJoCo no está disponible en el environment
- O no se está llamando correctamente desde run_simulation.py
- El pipeline está using render_simulation_video.py (matplotlib 2D) 
  en lugar de visualize_3d_mujoco.py (MuJoCo 3D)

ARCHIVOS INVOLUCRADOS:
1. tools/run_simulation.py - Orquestador principal
2. tools/render_simulation_video.py - Genera VIDEO 2D (matplotlib)
3. tools/visualization/visualize_3d_mujoco.py - Genera VIDEO 3D (MuJoCo)
4. tools/visualization/create_final_visualizations.py - Genera imágenes 2D/3D estáticas

INVESTIGACIÓN:
"""

import sys
from pathlib import Path
import importlib.util

print("\n" + "="*80)
print("MUJOCO VIDEO GENERATION DEBUG")
print("="*80)

# Check 1: FlyGym availability
print("\n1. Checking FlyGym availability...")
try:
    import flygym
    print(f"   [OK] FlyGym is installed")
    print(f"        Location: {flygym.__file__}")
    print(f"        Version: {getattr(flygym, '__version__', 'unknown')}")
    FLYGYM_AVAILABLE = True
except ImportError as e:
    print(f"   [FAIL] FlyGym NOT available")
    print(f"         Error: {e}")
    FLYGYM_AVAILABLE = False

# Check 2: MuJoCo availability
print("\n2. Checking MuJoCo availability...")
try:
    import mujoco
    print(f"   [OK] MuJoCo is installed")
    print(f"        Location: {mujoco.__file__}")
    MUJOCO_AVAILABLE = True
except ImportError as e:
    print(f"   [FAIL] MuJoCo NOT available")
    print(f"         Error: {e}")
    MUJOCO_AVAILABLE = False

# Check 3: Rendering dependencies
print("\n3. Checking rendering dependencies...")
try:
    import matplotlib.animation as animation
    print(f"   [OK] matplotlib.animation available")
except ImportError:
    print(f"   [FAIL] matplotlib.animation NOT available")

try:
    from matplotlib.animation import FFMpegWriter
    print(f"   [OK] FFMpegWriter available")
except ImportError:
    print(f"   [FAIL] FFMpegWriter NOT available")

# Check 4: Current visualization pipeline
print("\n4. Current visualization pipeline in run_simulation.py:")
print("""
    Lines ~270-290:
    if render_video and csv_path.exists():
        render_path = Path(__file__).parent / "render_simulation_video.py"
        
    This loads SimulationVideoRenderer from render_simulation_video.py
    which is  a MATPLOTLIB-based renderer (2D).
    
    NEVER LOADS: visualize_3d_mujoco.py (MuJoCo-based, 3D)
""")

# Check 5: MuJoCoVisualizer inspection
print("\n5. Inspecting MuJoCoVisualizer requirements...")
mujoco_viz_path = Path(__file__).parent.parent / "tools/visualization/visualize_3d_mujoco.py"
if mujoco_viz_path.exists():
    print(f"   [OK] visualize_3d_mujoco.py exists")
    
    # Try to load it
    try:
        spec = importlib.util.spec_from_file_location("mujoco_viz", str(mujoco_viz_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"   [OK] visualize_3d_mujoco.py can be imported")
        if hasattr(module, 'MuJoCoVisualizer'):
            print(f"   [OK] MuJoCoVisualizer class found")
        else:
            print(f"   [FAIL] MuJoCoVisualizer class NOT found")
    except Exception as e:
        print(f"   [FAIL] Cannot import visualize_3d_mujoco.py")
        print(f"          Error: {e}")
else:
    print(f"   [FAIL] visualize_3d_mujoco.py not found at {mujoco_viz_path}")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

if not FLYGYM_AVAILABLE or not MUJOCO_AVAILABLE:
    print("""
[ROOT CAUSE] FlyGym and/or MuJoCo are NOT installed or NOT in Python PATH.

SOLUTION OPTIONS:

Option A: Install FlyGym (recommended for full integration)
   pip install flygym

Option B: Use simplified 3D visualization without physics
   - Create a new script that:
     1. Reads trajectory CSV
     2. Uses the fly pose data directly
     3. Renders with matplotlib 3D or vispy
     4. Exports as MP4

Option C: Run on system with FlyGym already installed
   - Contact the FlyGym developers or local Python expert
   - FlyGym requires specific JAX/MuJoCo versions

CURRENT ISSUE:
   render_simulation_video.py uses matplotlib (2D)
   visualize_3d_mujoco.py requires FlyGym (NOT available)
   
   Result: User gets 2D video, not 3D
""")
else:
    print("""
[ISSUE] FlyGym and MuJoCo ARE available, but:
   run_simulation.py is NOT using visualize_3d_mujoco.py
   
SOLUTION:
   Modify run_simulation.py to call MuJoCoVisualizer instead of
   SimulationVideoRenderer when FlyGym is available.
""")

print("\nNEXT STEPS:")
print("="*80)
print("""
1. Verify FlyGym installation:
   python -c "import flygym; print(flygym.__version__)"

2. If FlyGym available:
   - Modify run_simulation.py to use visualize_3d_mujoco.py
   - Test with: python tools/visualization/visualize_3d_mujoco.py

3. If FlyGym NOT available:
   - Option A: Install FlyGym (requires JAX setup)
   - Option B: Create simplified 3D renderer using matplotlib.mplot3d
   - Option C: Use existing trajectory data to feed into MuJoCo separately

4. Create a proper MuJoCo integration that:
   a) Runs actual FlyGym simulation (not just trajectory tracking)
   b) Records video during actual simulation
   c) Outputs MP4 with real physics and kinematics
""")
