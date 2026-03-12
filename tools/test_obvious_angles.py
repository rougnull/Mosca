#!/usr/bin/env python3
"""
TEST SIMPLE: Renderizar ángulos OBVIOS
======================================
Genera un video donde aplicamos ángulos que claramente mueven las patas.
Útil para verificar que FlyGym está renderizando correctamente movimiento.
"""

import sys
from pathlib import Path
import numpy as np
import imageio

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from flygym import Fly, SingleFlySimulation
from flygym.arena import FlatTerrain
from flygym.preprogrammed import all_leg_dofs

print("\n" + "="*70)
print("TEST SIMPLE: ÁNGULOS OBVIOS")
print("="*70)

# Crear simulación
fly = Fly(init_pose="stretch", actuated_joints=all_leg_dofs, control="position")
sim = SingleFlySimulation(fly=fly, arena=FlatTerrain())
obs, info = sim.reset()

print("[*] Simulación inicializada")

# Crear 50 frames con ángulos que claramente varían
frames = []

print(f"[*] Generando 50 frames con ángulos variantes...")

for frame_idx in range(50):
    try:
        # Crear ángulos OBVIAMENTE diferentes que varían
        # Usar seno para que oscilen y el movimiento sea visible
        phase = (frame_idx / 50.0) * 2 * np.pi
        
        # Crear array de 42 ángulos que varían sinusoidalmente
        angles = np.zeros(42, dtype=np.float32)
        
        # Hacer que los ángulos varíen notablemente
        # Ejemplo: Femur (levantamiento principal) varía entre -0.5 y 0.5
        for i in range(42):
            # Diferentes fases para diferentes joints
            joint_phase = phase + (i / 42.0) * 2 * np.pi
            angles[i] = 0.3 * np.sin(joint_phase)  # Rango: -0.3 a 0.3 radianes
        
        action = {"joints": angles}
        
        # Step
        obs = sim.step(action)
        
        # Renderizar
        frame_list = sim.render()
        
        if frame_list and len(frame_list) > 0:
            frame = frame_list[0]
            if frame is not None:
                frames.append(frame)
                status = "[OK]"
            else:
                status = "[!] None"
        else:
            status = "[X] Empty"
        
        if (frame_idx + 1) % 10 == 0:
            print(f"  Frame {frame_idx+1:3d}/50 {status}")
    
    except Exception as e:
        print(f"  Frame {frame_idx:3d}: Error: {e}")

print(f"\n[*] Frames capturados: {len(frames)}")

if len(frames) > 0:
    # Guardar video
    output_path = PROJECT_ROOT / "outputs" / "simulations" / "test_obvious_angles.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Guardando video...")
    imageio.mimsave(str(output_path), frames, fps=30)
    
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Video guardado: {output_path}")
    print(f"    Tamaño: {file_size:.2f} MB")
    print(f"    Duración estimada: {len(frames) / 30:.2f} segundos")
else:
    print("[X] No se capturaron frames")

print("\n" + "="*70)
