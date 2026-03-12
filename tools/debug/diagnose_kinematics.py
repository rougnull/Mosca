#!/usr/bin/env python3
"""
TEST SIMPLE: Mini-simulación de 10 pasos
Ejecuta una simulación MÍNIMA y muestra lo que sucede en cada paso.
Útil para diagnosticar dónde falla la integración del movimiento.
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain

print("\n" + "="*70)
print("TEST SIMPLE: 10-STEP SIMULATION DIAGNOSTIC")
print("="*70)

# Parámetros
odor_source=(50.0, 50.0, 5.0)
odor_sigma=8.0
odor_amplitude=100.0
start_pos=np.array([35.0, 35.0, 3.0], dtype=float)
sim_dt=0.01
max_forward_speed=50.0
max_turn_rate=300.0

# Inicializar
odor_field = OdorField(sources=odor_source, sigma=odor_sigma, amplitude=odor_amplitude)
brain = ImprovedOlfactoryBrain(bilateral_distance=1.2, forward_scale=1.0, turn_scale=0.8, temporal_gradient_gain=10.0)

pos = start_pos.copy()
heading = np.arctan2(odor_source[1] - pos[1], odor_source[0] - pos[0])

print(f"\nINICIAL STATE:")
print(f"  Position: {pos}")
print(f"  Heading: {np.degrees(heading):.2f}°")
print(f"  Target (odor source): {odor_source}")

print(f"\nPARAMETRS:")
print(f"  Max forward speed: {max_forward_speed} mm/s")
print(f"  Max turn rate: {max_turn_rate} °/s")
print(f"  Timestep: {sim_dt} s")
print(f"  Expected displacement per step (max): {max_forward_speed * sim_dt} mm")

print("\n" + "-"*70)
print(f"{'Step':<5} | {'Conc':<8} | {'Fwd':<6} | {'Turn':<6} | {'X':<8} | {'Y':<8} | {'Head°':<7} | {'ΔX':<7} | {'ΔY':<7}")
print("-"*70)

positions_log = [pos.copy()]
headings_log = [heading]

for step_idx in range(10):
    # Brain decision
    action = brain.step(odor_field, pos, heading)
    forward_cmd = float(action[0])
    turn_cmd = float(action[1])
    
    # Get odor concentration
    conc = float(odor_field.concentration_at(pos))
    
    # Kinematics calculation
    linear_velocity = forward_cmd * max_forward_speed  # mm/s
    angular_velocity = turn_cmd * max_turn_rate * np.pi / 180.0  # rad/s
    
    # Integration
    heading += angular_velocity * sim_dt
    
    delta_pos = sim_dt * linear_velocity * np.array([
        np.cos(heading),
        np.sin(heading),
        0.0
    ])
    
    new_pos = pos + delta_pos
    
    # Bounds
    new_pos[0] = np.clip(new_pos[0], 0, 100)
    new_pos[1] = np.clip(new_pos[1], 0, 100)
    new_pos[2] = np.clip(new_pos[2], 0, 10)
    
    pos = new_pos
    
    # Log
    positions_log.append(pos.copy())
    headings_log.append(heading)
    
    # Display
    print(f"{step_idx:<5} | {conc:<8.4f} | {forward_cmd:<6.3f} | {turn_cmd:<6.3f} | {pos[0]:<8.2f} | {pos[1]:<8.2f} | {np.degrees(heading):<7.1f} | {delta_pos[0]:<7.3f} | {delta_pos[1]:<7.3f}")

print("-"*70)

# Analysis
positions = np.array(positions_log)
headings = np.array(headings_log)

print(f"\nFINAL STATE:")
print(f"  Position: {positions[-1]}")
print(f"  Heading: {np.degrees(headings[-1]):.2f}°")

print(f"\nTOTAL DISPLACEMENT:")
total_disp = positions[-1] - positions[0]
print(f"  ΔX: {total_disp[0]:.2f} mm")
print(f"  ΔY: {total_disp[1]:.2f} mm")
print(f"  Distance: {np.linalg.norm(total_disp[:2]):.2f} mm")

print(f"\nHEADING CHANGE:")
print(f"  Initial: {np.degrees(headings[0]):.2f}°")
print(f"  Final: {np.degrees(headings[-1]):.2f}°")
print(f"  Total change: {np.degrees(headings[-1] - headings[0]):.2f}°")

print(f"\nDIAGNOSTIC:")
if total_disp[0] > 0.01 or total_disp[1] > 0.01:
    print(f"  [OK] Movement detected")
else:
    print(f"  [X] NO MOVEMENT DETECTED - Problem in kinematics integration")

if abs(np.degrees(headings[-1] - headings[0])) > 0.1:
    print(f"  [OK] Heading change detected")
else:
    print(f"  [!] No heading change (turn_cmd was 0)")

print("\n" + "="*70)
