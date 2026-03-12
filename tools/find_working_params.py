"""
Script de diagnóstico mejorado: Busca parámetros que funcionen
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain


def analyze_field_reachability(source=(50, 50, 5), sigma=1.0, amplitude=10.0, threshold=0.01):
    """Analizar si el campo es detectable desde posición inicial típica"""
    
    odor_field = OdorField(sources=source, sigma=sigma, amplitude=amplitude)
    
    # Distancias típicas
    distances = np.linspace(10, 100, 100)
    concentrations = []
    
    for d in distances:
        # Posición a distancia d del origen (10, 10, 5)
        pos = np.array([10 + d * np.cos(np.pi/4), 10 + d * np.sin(np.pi/4), 5])
        conc = odor_field.concentration_at(pos)
        concentrations.append(conc)
    
    concentrations = np.array(concentrations)
    above_threshold = concentrations > threshold
    
    # Encontrar distancia máxima donde se puede detectar
    if np.any(above_threshold):
        max_detectable_dist = distances[np.where(above_threshold)[0][-1]]
    else:
        max_detectable_dist = 0
    
    return {
        "sigma": sigma,
        "amplitude": amplitude,
        "threshold": threshold,
        "max_conc": float(np.max(concentrations)),
        "max_detectable_distance": float(max_detectable_dist),
        "typical_initial_distance": 56.6,
        "detectable_from_typical_init": float(max_detectable_dist) >= 56.6
    }


def simulate_with_params(sigma, amplitude, threshold, duration=10):
    """Simular con parámetros dados"""
    
    dt = 0.01
    num_steps = int(duration / dt)
    
    odor_field = OdorField(sources=(50, 50, 5), sigma=sigma, amplitude=amplitude)
    brain = OlfactoryBrain(threshold=threshold, mode="gradient", forward_scale=1.0, turn_scale=1.0)
    
    position = np.array([10.0, 10.0, 5.0])
    heading = 0.0
    
    odor_log = []
    distances = []
    max_conc_detected = 0
    
    for step in range(num_steps):
        conc = odor_field.concentration_at(position)
        max_conc_detected = max(max_conc_detected, conc)
        odor_log.append(conc)
        
        action = brain.step(conc)
        heading += np.deg2rad(action[1] * 90 * dt)
        velocity = 10 * action[0]
        delta = np.array([
            velocity * np.cos(heading) * dt,
            velocity * np.sin(heading) * dt,
            0
        ])
        position = position + delta
        position[0] = np.clip(position[0], 0, 100)
        position[1] = np.clip(position[1], 0, 100)
        
        dist = np.linalg.norm(position[:2] - np.array([50, 50]))
        distances.append(dist)
    
    return {
        "sigma": sigma,
        "amplitude": amplitude,
        "threshold": threshold,
        "max_odor_detected": float(max_conc_detected),
        "initial_distance": float(distances[0]),
        "final_distance": float(distances[-1]),
        "min_distance": float(np.min(distances)),
        "improvement": float(distances[0] - distances[-1]),
        "mean_odor": float(np.mean(odor_log))
    }


print("\n" + "="*70)
print("ANÁLISIS PARAMÉTRICO: Búsqueda de configuración funcional")
print("="*70)

print("\n1. Evaluando REACHABILITY (¿se detecta desde 56.6mm?)")
print("-"*70)

test_params = [
    # (sigma, amplitude, threshold)
    (1.0, 1.0, 0.01),
    (1.0, 5.0, 0.01),
    (1.0, 10.0, 0.01),
    (2.0, 5.0, 0.01),
    (0.5, 5.0, 0.01),
    (3.0, 10.0, 0.01),
]

reachability_results = {}
for sigma, amplitude, threshold in test_params:
    result = analyze_field_reachability(sigma=sigma, amplitude=amplitude, threshold=threshold)
    key = f"sigma{sigma}_amp{amplitude}"
    reachability_results[key] = result
    detectable = "✓ SÍ" if result["detectable_from_typical_init"] else "✗ NO"
    print(f"  sigma={sigma}, amp={amplitude}: max_det_dist={result['max_detectable_distance']:.1f}mm {detectable}")

print("\n2. Simulando configuraciones REACHABLE")
print("-"*70)

# Tomar las que funcionan
valid_configs = [
    (1.0, 10.0, 0.01),
    (1.0, 5.0, 0.01),
    (0.5, 10.0, 0.01),
    (2.0, 10.0, 0.01),
]

simulation_results = {}
for sigma, amplitude, threshold in valid_configs:
    result = simulate_with_params(sigma, amplitude, threshold)
    key = f"sigma{sigma}_amp{amplitude}_thresh{threshold}"
    simulation_results[key] = result
    
    print(f"\n  Config: sigma={sigma}, amp={amplitude}, thresh={threshold}")
    print(f"    Max odor detected: {result['max_odor_detected']:.6f}")
    print(f"    Final distance: {result['final_distance']:.1f}mm")
    print(f"    Improvement: {result['improvement']:.1f}mm")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

# Encontrar mejor config
best_config = max(simulation_results.items(), key=lambda x: x[1]['improvement'])
print(f"\nMejor configuración: {best_config[0]}")
print(f"  Mejora: {best_config[1]['improvement']:.1f}mm")
print(f"  Distancia final: {best_config[1]['final_distance']:.1f}mm")

# Guardar results
output_file = Path("outputs/Experiment - 2026-03-12_11_57/parameter_search.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, "w") as f:
    json.dump({
        "reachability": reachability_results,
        "simulations": simulation_results,
        "best_config": {
            "config_name": best_config[0],
            "metrics": best_config[1]
        }
    }, f, indent=2)

print(f"\n✓ Resultados guardados en: {output_file}")
