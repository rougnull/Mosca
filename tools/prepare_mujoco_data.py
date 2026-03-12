"""
Preparación de datos para simulación 3D con MuJoCo

Toma los datos de navegación olfatoria y los convierte en comandos
motores que pueden alimentarse al cuerpo 3D de la mosca en MuJoCo.
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def load_working_simulation_trajectory(sim_dir):
    """Cargar trayectoria de una simulación exitosa"""
    
    trajectory_file = Path(sim_dir) / "trajectory.csv"
    
    data = {}
    with open(trajectory_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            step = int(row["step"])
            data[step] = {
                "position": np.array([float(row["x_mm"]), float(row["y_mm"]), float(row["z_mm"])]) / 1000,  # Convertir a metros
                "odor": float(row["odor_conc"]),
                "forward": float(row["forward_cmd"]),
                "turn": float(row["turn_cmd"]),
                "distance": float(row["distance_to_source_mm"])
            }
    
    return data


def extract_joint_commands(trajectory_data, dt=0.01):
    """
    Extraer comandos de articulaciones from navegación olfatoria.
    
    Para una mosca, necesitamos:
    - Velocidades de las alas (movimiento hacia adelante/atrás)
    - Velocidades de las patas traseras (giro, estabilidad)
    - Posición del cuerpo
    
    Esto es una interpretación simplificada: usaremos los comandos forward/turn
    para generar velocidades esperadas que luego MuJoCo puede interpretar.
    """
    
    joint_commands = []
    
    for step in sorted(trajectory_data.keys()):
        data = trajectory_data[step]
        
        # Comandos de navegación
        forward_cmd = data["forward"]  # -1 a 1
        turn_cmd = data["turn"]        # -1 a 1
        
        # Mapear a velocidades físicas (valores típicos para mosca FlyGym)
        # Velocidades de alas típicas: 0-200 Hz, nos limitamos a -1 a 1 para normalización
        wing_speed = forward_cmd * 150  # Hz (movimiento hacia adelante aumenta frecuencia)
        
        # Velocidades de patas traseras para giro (afecta torsión)
        L_hind_leg_speed = turn_cmd * 0.5   # Proporcional a comando de giro
        R_hind_leg_speed = -turn_cmd * 0.5  # Opuesto para giro
        
        joint_commands.append({
            "step": step,
            "time_seconds": step * dt,
            "position_world_m": data["position"].tolist(),
            "position_world_mm": [data["position"][i] * 1000 for i in range(3)],
            "odor_concentration": data["odor"],
            "navigation_commands": {
                "forward": forward_cmd,
                "turn": turn_cmd
            },
            "motor_outputs": {
                "wing_frequency_Hz": float(wing_speed),
                "left_hind_leg_speed": float(L_hind_leg_speed),
                "right_hind_leg_speed": float(R_hind_leg_speed),
            },
            "distance_to_source_mm": data["distance"]
        })
    
    return joint_commands


def generate_mujoco_control_sequence(trajectory_data, sim_name):
    """
    Generar un archivo de controles listo para MuJoCo
    """
    
    joint_commands = extract_joint_commands(trajectory_data)
    
    output_data = {
        "metadata": {
            "simulation_name": sim_name,
            "generated_at": datetime.now().isoformat(),
            "description": "Motor commands extracted from olfactory navigation simulation",
            "total_steps": len(joint_commands),
            "dt_seconds": 0.01,
            "total_duration_seconds": len(joint_commands) * 0.01,
        },
        "motor_commands": joint_commands
    }
    
    return output_data


# =============================================================================
# Procesar las simulaciones exitosas
# =============================================================================

experiment_dir = Path("outputs") / "Experiment - 2026-03-12_11_59"

# Identificar simulaciones exitosas
successful_sims = [
    "broad_field_detection",
    "optimized_sigma15_near"
]

print("\n" + "="*70)
print("PREPARACIÓN DE DATOS PARA MUJOCO 3D")
print("="*70)

for sim_name in successful_sims:
    sim_dir = experiment_dir / sim_name
    
    if not sim_dir.exists():
        print(f"\n✗ No encontrada: {sim_name}")
        continue
    
    print(f"\n{sim_name}:")
    
    # Cargar trayectoria
    trajectory_data = load_working_simulation_trajectory(sim_dir)
    print(f"  ✓ Datos cargados: {len(trajectory_data)} pasos")
    
    # Generar comandos para MuJoCo
    mujoco_data = generate_mujoco_control_sequence(trajectory_data, sim_name)
    
    # Guardar
    output_file = sim_dir / f"{sim_name}_mujoco_commands.json"
    with open(output_file, 'w') as f:
        json.dump(mujoco_data, f, indent=2)
    
    print(f"  ✓ Comandos MuJoCo guardados: {output_file.name}")
    print(f"    - Total pasos: {len(mujoco_data['motor_commands'])}")
    print(f"    - Duración: {mujoco_data['metadata']['total_duration_seconds']:.1f}s")
    
    # Guardar también como CSV para verificación rápida
    csv_file = sim_dir / f"{sim_name}_mujoco_commands.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["step", "time_s", "x_mm", "y_mm", "z_mm", "odor", 
                        "forward_cmd", "turn_cmd", "wing_Hz", "left_leg", "right_leg"])
        
        for cmd in mujoco_data['motor_commands']:
            writer.writerow([
                cmd["step"],
                cmd["time_seconds"],
                cmd["position_world_mm"][0],
                cmd["position_world_mm"][1],
                cmd["position_world_mm"][2],
                cmd["odor_concentration"],
                cmd["navigation_commands"]["forward"],
                cmd["navigation_commands"]["turn"],
                cmd["motor_outputs"]["wing_frequency_Hz"],
                cmd["motor_outputs"]["left_hind_leg_speed"],
                cmd["motor_outputs"]["right_hind_leg_speed"],
            ])
    
    print(f"  ✓ CSV para verificación: {csv_file.name}")

print("\n" + "="*70)
print("PASOS SIGUIENTES PARA MUJOCO 3D:")
print("="*70)
print("""
1. Cargar el modelo de mosca 3D (XML de MuJoCo)
2. Para cada paso en el archivo de comandos:
   - Actualizar posición del cuerpo principal
   - Aplicar velocidades angulares a las articulaciones
   - Ejecutar simulación física de MuJoCo
   - Guardar frame para visualización

Requisitos:
- Modelo 3D de mosca en formato MuJoCo XML
- Mapeo de comandos motores a articulaciones físicas
- Renderer de MuJoCo o exportador a video
""")
