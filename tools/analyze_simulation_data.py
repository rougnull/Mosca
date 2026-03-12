#!/usr/bin/env python3
"""
Análisis de Simulación - Diagnóstico de Problemas
==================================================

Analiza el archivo .pkl de la simulación para diagnosticar:
1. Comportamiento del motor físico (física de MuJoCo)
2. Comportamiento de las extremidades (ángulos de joints)
3. Comportamiento del cerebro (acciones motoras)
4. Comportamiento del rendering (orientación y posición)

USO:
    python tools/analyze_simulation_data.py outputs/simulations/chemotaxis_3d/2026-03-12_16_49/simulation_trajectory_3d.pkl
"""

import sys
import pickle
import numpy as np
from pathlib import Path
import json

def analyze_pkl_file(pkl_path):
    """Analizar archivo .pkl de simulación."""
    print("="*70)
    print("ANÁLISIS DE DATOS DE SIMULACIÓN")
    print("="*70)
    print(f"Archivo: {pkl_path}\n")

    # Cargar datos
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f)

    print(f"Tipo de datos: {type(data)}")

    if isinstance(data, dict):
        print(f"\nClaves en datos: {list(data.keys())[:20]}")

        # Analizar cada clave
        for key in list(data.keys())[:5]:
            value = data[key]
            print(f"\n{key}:")
            print(f"  Tipo: {type(value)}")
            if hasattr(value, 'shape'):
                print(f"  Shape: {value.shape}")
                if len(value.shape) > 0 and value.shape[0] > 0:
                    print(f"  Primeros valores: {value[:3]}")
                    print(f"  Últimos valores: {value[-3:]}")
            elif isinstance(value, (list, tuple)):
                print(f"  Longitud: {len(value)}")
                if len(value) > 0:
                    print(f"  Tipo primer elemento: {type(value[0])}")
                    if hasattr(value[0], 'shape'):
                        print(f"  Shape primer elemento: {value[0].shape}")

        # Buscar información crítica
        print("\n" + "="*70)
        print("ANÁLISIS DE INFORMACIÓN CRÍTICA")
        print("="*70)

        # 1. Posición y orientación
        if any('pos' in k.lower() for k in data.keys()):
            print("\n1. POSICIÓN:")
            for key in data.keys():
                if 'pos' in key.lower():
                    value = data[key]
                    if hasattr(value, 'shape') and len(value.shape) > 0:
                        print(f"  {key}: shape={value.shape}")
                        # Analizar si se hunde
                        if value.shape[-1] >= 3:  # tiene x, y, z
                            z_values = value[:, 2] if len(value.shape) == 2 else value[2]
                            if isinstance(z_values, np.ndarray):
                                print(f"    Z inicial: {z_values[0]:.4f}")
                                print(f"    Z final: {z_values[-1]:.4f}")
                                print(f"    Z mínimo: {np.min(z_values):.4f}")
                                print(f"    Z máximo: {np.max(z_values):.4f}")
                                if np.min(z_values) < 0:
                                    print(f"    ⚠️  PROBLEMA: La mosca se hundió bajo el suelo (Z < 0)")

        if any('orient' in k.lower() or 'heading' in k.lower() or 'quat' in k.lower() for k in data.keys()):
            print("\n2. ORIENTACIÓN:")
            for key in data.keys():
                if any(x in key.lower() for x in ['orient', 'heading', 'quat', 'rotation']):
                    value = data[key]
                    if hasattr(value, 'shape'):
                        print(f"  {key}: shape={value.shape}")
                        if len(value.shape) > 0 and value.shape[0] > 0:
                            print(f"    Inicial: {value[0]}")
                            print(f"    Final: {value[-1]}")
                            # Si es ángulo, convertir a grados
                            if value.shape[-1] == 1 or (len(value.shape) == 1):
                                initial_deg = np.degrees(value[0] if isinstance(value[0], (int, float)) else value[0, 0])
                                final_deg = np.degrees(value[-1] if isinstance(value[-1], (int, float)) else value[-1, 0])
                                print(f"    Inicial (grados): {initial_deg:.1f}°")
                                print(f"    Final (grados): {final_deg:.1f}°")
                                rotation = abs(final_deg - initial_deg)
                                if rotation > 170 and rotation < 190:
                                    print(f"    ⚠️  PROBLEMA: Rotación ~180° detectada ({rotation:.1f}°)")

        # 3. Ángulos de joints
        if any('joint' in k.lower() or 'angle' in k.lower() for k in data.keys()):
            print("\n3. ÁNGULOS DE JOINTS:")
            joint_keys = [k for k in data.keys() if 'joint' in k.lower() or 'angle' in k.lower()]
            print(f"  Encontrados {len(joint_keys)} joints")
            if joint_keys:
                key = joint_keys[0]
                value = data[key]
                if hasattr(value, 'shape'):
                    print(f"  Ejemplo ({key}): shape={value.shape}")
                    if len(value.shape) > 0 and value.shape[0] > 0:
                        print(f"    Valores iniciales: {value[0][:5] if len(value.shape) > 1 else value[:5]}")
                        print(f"    Rango: [{np.min(value):.4f}, {np.max(value):.4f}]")
                        # Verificar si están todos en 0 (patas rectas)
                        if np.allclose(value, 0, atol=0.01):
                            print(f"    ⚠️  PROBLEMA: Todos los ángulos ~0 (patas rectas/no se mueven)")

        # 4. Acciones motoras
        if any('action' in k.lower() or 'forward' in k.lower() or 'turn' in k.lower() for k in data.keys()):
            print("\n4. ACCIONES MOTORAS:")
            for key in data.keys():
                if any(x in key.lower() for x in ['action', 'forward', 'turn', 'motor']):
                    value = data[key]
                    if hasattr(value, 'shape'):
                        print(f"  {key}: shape={value.shape}")
                        if len(value.shape) > 0 and value.shape[0] > 0:
                            print(f"    Media: {np.mean(value, axis=0)}")
                            print(f"    Std: {np.std(value, axis=0)}")
                            # Verificar si hay movimiento
                            if np.allclose(value, 0, atol=0.01):
                                print(f"    ⚠️  PROBLEMA: No hay acciones motoras (todo ~0)")

        # 5. Timesteps/frames
        print("\n5. INFORMACIÓN DE TIEMPO:")
        if 'times' in data or 'timestamps' in data or 'time' in data:
            time_key = 'times' if 'times' in data else 'timestamps' if 'timestamps' in data else 'time'
            times = data[time_key]
            if hasattr(times, '__len__'):
                print(f"  Total de frames: {len(times)}")
                if len(times) > 1:
                    dt = times[1] - times[0] if isinstance(times[0], (int, float)) else times[1][0] - times[0][0]
                    fps_sim = 1.0 / dt if dt > 0 else 0
                    print(f"  dt entre frames: {dt:.6f}s")
                    print(f"  FPS simulación: {fps_sim:.1f}")
                    if fps_sim < 10:
                        print(f"    ⚠️  PROBLEMA: FPS muy bajo ({fps_sim:.1f} fps)")

    elif isinstance(data, list):
        print(f"\nLista de {len(data)} elementos")
        if len(data) > 0:
            print(f"Tipo primer elemento: {type(data[0])}")
            if isinstance(data[0], dict):
                print(f"Claves primer elemento: {list(data[0].keys())[:10]}")

    print("\n" + "="*70)
    print("FIN DEL ANÁLISIS")
    print("="*70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analyze_simulation_data.py <archivo.pkl>")
        sys.exit(1)

    pkl_file = sys.argv[1]
    if not Path(pkl_file).exists():
        print(f"Error: Archivo no encontrado: {pkl_file}")
        sys.exit(1)

    analyze_pkl_file(pkl_file)
