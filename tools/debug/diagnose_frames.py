#!/usr/bin/env python3
"""
DIAGNÓSTICO DETALLADO DE FRAMES
==============================
Inspecciona exactamente qué frames se están capturando y cómo se ven.
Útil para identificar si los frames son válidos o si hay un problema en sim.render()
"""

import sys
from pathlib import Path
import numpy as np
import pickle

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from flygym import Fly, SingleFlySimulation
from flygym.arena import FlatTerrain
from flygym.preprogrammed import all_leg_dofs
from core.data import format_joint_data

print("\n" + "="*70)
print("DIAGNÓSTICO DETALLADO DE FRAMES")
print("="*70)

# Cargar datos de simulación
simulations_dir = PROJECT_ROOT / "outputs" / "simulations"
pkl_files = sorted(list(simulations_dir.glob("**/simulation_trajectory_3d.pkl")))

if not pkl_files:
    print("[X] No hay archivos .pkl para diagnosticar")
    exit(1)

pkl_file = pkl_files[-1]
print(f"\n[*] Cargando: {pkl_file.relative_to(PROJECT_ROOT)}")

with open(pkl_file, "rb") as f:
    data = pickle.load(f)

# Format joint data
formatted_data = format_joint_data(data, subsample=1)
joint_names = sorted(list(formatted_data.keys()))

print(f"[*] {len(joint_names)} joints detectados")

n_frames = len(formatted_data[joint_names[0]])
print(f"[*] {n_frames} frames en datos")

# Setup simulación
fly = Fly(init_pose="stretch", actuated_joints=all_leg_dofs, control="position")
sim = SingleFlySimulation(fly=fly, arena=FlatTerrain())
obs, info = sim.reset()

print(f"\n[*] Inspeccionando frames renderizados...")

# Probar renderizado de primeros 5 frames
frame_samples = []
frame_info = {}

for frame_idx in [0, 1, 2, 4, 9]:
    if frame_idx >= n_frames:
        break
    
    try:
        # Compilar acción
        action_values = []
        for joint_name in joint_names:
            val = float(formatted_data[joint_name][frame_idx])
            action_values.append(val)
        
        action = {"joints": np.array(action_values, dtype=np.float32)}
        obs = sim.step(action)
        
        # Renderizar
        frame_list = sim.render()
        
        print(f"\n  Frame {frame_idx}:")
        print(f"    sim.render() retornó: {type(frame_list)}")
        
        if frame_list is None:
            print(f"    [X] Valor None")
        elif isinstance(frame_list, list):
            print(f"    [*] Lista con {len(frame_list)} elementos")
            if len(frame_list) > 0:
                frame = frame_list[0]
                print(f"        Frame[0]: type={type(frame)}, shape={frame.shape if hasattr(frame, 'shape') else 'N/A'}, dtype={frame.dtype if hasattr(frame, 'dtype') else 'N/A'}")
                
                if isinstance(frame, np.ndarray):
                    print(f"        Min={frame.min():.1f}, Max={frame.max():.1f}, Mean={frame.mean():.1f}")
                    
                    # Calcular histograma
                    unique_vals = len(np.unique(frame))
                    if unique_vals < 1000:
                        print(f"        [!] Valores únicos: {unique_vals} (potencial bajo contenido)")
                    
                    frame_samples.append(frame)
                    frame_info[frame_idx] = {
                        "shape": frame.shape,
                        "dtype": frame.dtype,
                        "min": float(frame.min()),
                        "max": float(frame.max()),
                        "unique": unique_vals
                    }
        else:
            print(f"    [X] Tipo inesperado: {type(frame_list)}")
    
    except Exception as e:
        print(f"    [X] Error: {e}")

# Análisis
print("\n" + "-"*70)
print("ANÁLISIS DE FRAMES")
print("-"*70)

if frame_samples:
    # Comparar frames
    print(f"\n[*] Comparando primeros frames capturados...")
    
    if len(frame_samples) > 1:
        # Calcular diferencia entre primeros frames
        diff = np.abs(frame_samples[1].astype(float) - frame_samples[0].astype(float))
        print(f"  Diferencia Frame[0] vs Frame[1]:")
        print(f"    Min diferencia: {diff.min():.1f}")
        print(f"    Max diferencia: {diff.max():.1f}")
        print(f"    Media diferencia: {diff.mean():.1f}")
        print(f"    Píxeles diferentes: {(diff > 0).sum()} de {diff.size}")
        
        if (diff > 0).sum() < diff.size * 0.1:
            print(f"\n  [!] ADVERTENCIA: Menos del 10% de píxeles cambian entre frames")
            print(f"      Esto sugiere que sim.render() no está capturando movimiento")
    
    # Inspeccionar si frames son completamente negros o blancos
    if frame_samples[0].min() == frame_samples[0].max():
        print(f"\n  [!] ADVERTENCIA: Frame 0 es uniforme (todos los píxeles iguales)")
    
    print(f"\n[*] Info de frames capturados:")
    for frame_idx, info in frame_info.items():
        print(f"    Frame {frame_idx}: {info['shape']}, dtype={info['dtype']}, valores=[{info['min']:.0f}, {info['max']:.0f}], únicos={info['unique']}")
else:
    print("\n[X] No se capturaron frames válidos")

print("\n" + "="*70)
