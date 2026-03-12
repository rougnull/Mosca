#!/usr/bin/env python3
"""
Test: Ejecutar SOLO simulación olfatoria sin renderizado
Para verificar que el movimiento se genera correctamente
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain

print("="*70)
print("TEST: Simulación Olfatoria sin Renderizado")
print("="*70)
print()

# Configuración
odor_source = (50.0, 50.0, 5.0)
odor_sigma = 8.0
odor_amplitude = 100.0
start_pos = (35.0, 35.0, 3.0)
n_steps = 50  # Solo 50 pasos para debugging rápido

print(f"Configuración:")
print(f"  Fuente de olor: {odor_source}")
print(f"  Sigma: {odor_sigma} mm")
print(f"  Amplitud: {odor_amplitude}")
print(f"  Posición inicio: {start_pos}")
print(f"  Steps: {n_steps}")
print()

# Inicializar
odor_field = OdorField(
    sources=odor_source,
    sigma=odor_sigma,
    amplitude=odor_amplitude
)

brain = ImprovedOlfactoryBrain(
    bilateral_distance=1.2,
    forward_scale=1.0,
    turn_scale=0.8,
    temporal_gradient_gain=10.0
)

pos = np.array(start_pos, dtype=float)
heading = 0.7854  # 45°

positions = []
headings = []
actions_list = []
concentrations = []

print("Simulando...")
for step in range(n_steps):
    # Sensado y decisión
    action = brain.step(odor_field, pos, heading)
    forward_cmd = float(action[0])
    turn_cmd = float(action[1])
    
    # Cinemática
    max_forward_speed = 50.0  # mm/s
    max_turn_rate = 300.0     # deg/s
    sim_dt = 0.01
    
    linear_velocity = forward_cmd * max_forward_speed
    angular_velocity = turn_cmd * max_turn_rate * np.pi / 180.0
    
    # Integración
    heading += angular_velocity * sim_dt
    new_pos = pos + sim_dt * linear_velocity * np.array([
        np.cos(heading),
        np.sin(heading),
        0.0
    ])
    
    # Bounds
    new_pos[0] = np.clip(new_pos[0], 0, 100)
    new_pos[1] = np.clip(new_pos[1], 0, 100)
    new_pos[2] = np.clip(new_pos[2], 0, 10)
    
    pos = new_pos
    
    # Log
    conc = odor_field.concentration_at(pos)
    positions.append(pos.copy())
    headings.append(heading)
    actions_list.append([forward_cmd, turn_cmd])
    concentrations.append(conc)
    
    if step % 10 == 0:
        dist = np.linalg.norm(pos - np.array(start_pos))
        print(f"  Step {step:3d}: pos={pos}, heading={np.degrees(heading):6.1f}°, action=[{forward_cmd:.1f}, {turn_cmd:.1f}], conc={conc:.2e}, dist={dist:.2f}mm")

print()
print("Resultados:")
positions = np.array(positions)
headings = np.array(headings)
actions = np.array(actions_list)
concentrations = np.array(concentrations)

print(f"  Posición inicial: {positions[0]}")
print(f"  Posición final:   {positions[-1]}")
print(f"  Distancia total:  {np.linalg.norm(positions[-1] - positions[0]):.2f} mm")
print()

print(f"  Heading inicial: {np.degrees(headings[0]):.1f}°")
print(f"  Heading final:   {np.degrees(headings[-1]):.1f}°")
print(f"  Cambio heading:  {np.degrees(headings[-1] - headings[0]):.1f}°")
print()

print(f"  Comando forward: min={actions[:, 0].min():.2f}, max={actions[:, 0].max():.2f}, media={actions[:, 0].mean():.2f}")
print(f"  Comando turn:    min={actions[:, 1].min():.2f}, max={actions[:, 1].max():.2f}, media={actions[:, 1].mean():.2f}")
print()

print(f"  Concentración: min={concentrations.min():.2e}, max={concentrations.max():.2e}")
print()

# Análisis
if np.linalg.norm(positions[-1] - positions[0]) < 1.0:
    print("❌ PROBLEMA: Mosca casi no se movió")
elif actions[:, 0].max() < 0.1:
    print("❌ PROBLEMA: Comandos forward muy bajos")
else:
    print("✓ Simulación olfatoria parece estar funcionando")
