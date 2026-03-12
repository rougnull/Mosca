#!/usr/bin/env python3
"""
DIAGNÓSTICO CRÍTICO: FlyGym render() behavior
==============================================
Verifica exactamente qué hace render() en cada step
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from flygym import Fly, SingleFlySimulation
from flygym.arena import FlatTerrain
from flygym.preprogrammed import all_leg_dofs

print("\n" + "="*70)
print("DIAGNÓSTICO: FlyGym sim.render() BEHAVIOR")
print("="*70)

# Crear simulación con configuración mínima
fly = Fly(init_pose="stretch", actuated_joints=all_leg_dofs, control="position")
sim = SingleFlySimulation(fly=fly, arena=FlatTerrain())

print(f"\n[*] Simulación configurada")
print(f"    sim.render_interval: {getattr(sim, 'render_interval', 'NO TIENE')}")
print(f"    sim.timestep: {getattr(sim, 'timestep', 'NO TIENE')}")
print(f"    sim._render_camera: {hasattr(sim, '_render_camera')}")
print(f"    sim.camera: {hasattr(sim, 'camera')}")

# Investigar estructura de la simulación
print(f"\n[*] Atributos importantes de sim:")
relevant_attrs = [attr for attr in dir(sim) if 'render' in attr.lower() or 'camera' in attr.lower()]
for attr in relevant_attrs:
    try:
        val = getattr(sim, attr)
        print(f"    sim.{attr} = {type(val).__name__}")
    except:
        pass

# Resetear
obs, info = sim.reset()
print(f"\n[*] Simulación reseteada")
print(f"    Primer render():")

for i in range(3):
    # Crear acción simple
    action = {"joints": np.zeros(42, dtype=np.float32)}
    obs = sim.step(action)
    
    # Intentar render
    try:
        result = sim.render()
        print(f"\n  Step {i}:")
        print(f"    render() retornó: {type(result)}")
        if result is not None:
            print(f"    Longitud: {len(result) if isinstance(result, (list, tuple)) else 'N/A'}")
            if isinstance(result, (list, tuple)) and len(result) > 0:
                print(f"    [0] type: {type(result[0])}")
                if result[0] is not None and hasattr(result[0], 'shape'):
                    print(f"    [0] shape: {result[0].shape}")
        else:
            print(f"    [X] None")
    except Exception as e:
        print(f"\n  Step {i}: ERROR: {e}")
        import traceback
        traceback.print_exc()

# Intentar especificar parámetros diferentes
print(f"\n[*] Intentando render(mode='rgb_array'):")
try:
    result2 = sim.render(mode="rgb_array")
    print(f"    Retornó: {type(result2)}, shape={result2.shape if hasattr(result2, 'shape') else 'N/A'}")
except TypeError:
    print(f"    [X] mode parameter no soportado")
except Exception as e:
    print(f"    [X] Error: {e}")

print("\n" + "="*70)
