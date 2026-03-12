"""
Simulación FUNCIONAL de navegación olfatoria
Parámetros ajustados según diagnóstico
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


def run_working_simulation(sigma, amplitude, threshold, initial_pos, duration=30):
    """Ejecutar simulación con parámetros dados"""
    
    dt = 0.01
    num_steps = int(duration / dt)
    source = np.array([50.0, 50.0, 5.0])
    
    odor_field = OdorField(sources=source, sigma=sigma, amplitude=amplitude)
    brain = OlfactoryBrain(threshold=threshold, mode="gradient", forward_scale=1.0, turn_scale=1.0)
    
    position = np.array(initial_pos)
    heading = 0.0
    
    # Logs
    trajectory = []
    odor_log = []
    action_log = []
    distances = []
    concentrations_above_threshold = 0
    
    print(f"\n  Iniciando simulación:")
    print(f"    Posición inicial: {initial_pos}")
    print(f"    Parámetros: sigma={sigma}, amp={amplitude}, thresh={threshold}")
    
    for step in range(num_steps):
        # Sensor
        conc = odor_field.concentration_at(position)
        odor_log.append(conc)
        
        if conc > threshold:
            concentrations_above_threshold += 1
        
        # Cerebro
        action = brain.step(conc)
        action_log.append(action)
        
        # Actuadores
        heading += np.deg2rad(action[1] * 90 * dt)
        velocity = 10 * action[0]
        position = position + np.array([
            velocity * np.cos(heading) * dt,
            velocity * np.sin(heading) * dt,
            0
        ])
        
        # Límites arena
        position[0] = np.clip(position[0], 0, 100)
        position[1] = np.clip(position[1], 0, 100)
        
        trajectory.append(position.copy())
        dist = np.linalg.norm(position[:2] - source[:2])
        distances.append(dist)
        
        if (step + 1) % 1000 == 0:
            print(f"      Step {step + 1}/{num_steps}: conc={conc:.6f}, dist={dist:.1f}mm")
    
    trajectory = np.array(trajectory)
    odor_log = np.array(odor_log)
    action_log = np.array(action_log)
    distances = np.array(distances)
    
    metrics = {
        "config": {
            "sigma": sigma,
            "amplitude": amplitude,
            "threshold": threshold,
            "initial_position": list(initial_pos),
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        },
        "results": {
            "n_steps": num_steps,
            "mean_odor": float(np.mean(odor_log)),
            "max_odor": float(np.max(odor_log)),
            "min_odor": float(np.min(odor_log)),
            "std_odor": float(np.std(odor_log)),
            "steps_above_threshold": int(concentrations_above_threshold),
            "percent_above_threshold": float(100 * concentrations_above_threshold / num_steps),
            "initial_distance": float(distances[0]),
            "final_distance": float(distances[-1]),
            "min_distance": float(np.min(distances)),
            "total_improvement": float(distances[0] - distances[-1]),
            "success": bool(distances[-1] < distances[0]),
        }
    }
    
    return trajectory, odor_log, action_log, distances, metrics


def save_simulation_data(trajectory, odor_log, action_log, distances, metrics, sim_name, experiment_dir):
    """Guardar datos en formato CSV"""
    
    sim_dir = Path(experiment_dir) / sim_name
    sim_dir.mkdir(parents=True, exist_ok=True)
    
    # Guardar config y métricas
    with open(sim_dir / "config.json", "w") as f:
        json.dump(metrics["config"], f, indent=2)
    
    with open(sim_dir / "results.json", "w") as f:
        json.dump(metrics["results"], f, indent=2)
    
    # Guardar trayectoria
    with open(sim_dir / "trajectory.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["step", "x_mm", "y_mm", "z_mm", "odor_conc", "forward_cmd", "turn_cmd", "distance_to_source_mm"])
        for i in range(len(trajectory)):
            writer.writerow([
                i,
                trajectory[i, 0],
                trajectory[i, 1],
                trajectory[i, 2],
                odor_log[i],
                action_log[i, 0],
                action_log[i, 1],
                distances[i]
            ])
    
    print(f"    ✓ Datos guardados en: {sim_dir.name}/")
    
    return metrics["results"]


# =============================================================================
# EJECUTAR SIMULACIONES CON PARÁMETROS FUNCIONALES
# =============================================================================

print("\n" + "="*70)
print("SIMULACIONES FUNCIONALES DE NAVEGACIÓN OLFATORIA")
print("="*70)

# Crear directorio de experimento con estructura organizada
timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M")
experiment_dir = Path("outputs") / f"Experiment - {timestamp}"
experiment_dir.mkdir(parents=True, exist_ok=True)

all_results = {
    "timestamp": timestamp,
    "simulations": {}
}

# CONFIGURACIÓN 1: Parámetros diagnóstico fallidos (para comparación)
print("\n1. Replicando experimento fallido (control negativo)")
print("-"*70)

config1 = {
    "sigma": 15.0,
    "amplitude": 1.0,
    "threshold": 0.1,
    "initial_pos": [10, 10, 5],
    "name": "failed_original_params"
}

try:
    traj, odor, actions, dists, metrics = run_working_simulation(
        config1["sigma"], config1["amplitude"], config1["threshold"],
        config1["initial_pos"], duration=10
    )
    results = save_simulation_data(traj, odor, actions, dists, metrics, config1["name"], experiment_dir)
    all_results["simulations"][config1["name"]] = metrics
except Exception as e:
    print(f"    Error: {e}")


# CONFIGURACIÓN 2: Parámetros AMPLIOS (para detección lejana)
print("\n2. Parámetros amplios: sigma grande para detectar desde lejos")
print("-"*70)

config2 = {
    "sigma": 20.0,
    "amplitude": 1.0,
    "threshold": 0.005,
    "initial_pos": [10, 10, 5],
    "name": "broad_field_detection"
}

try:
    traj, odor, actions, dists, metrics = run_working_simulation(
        config2["sigma"], config2["amplitude"], config2["threshold"],
        config2["initial_pos"], duration=30
    )
    results = save_simulation_data(traj, odor, actions, dists, metrics, config2["name"], experiment_dir)
    all_results["simulations"][config2["name"]] = metrics
except Exception as e:
    print(f"    Error: {e}")


# CONFIGURACIÓN 3: Posición inicial cercana
print("\n3. Posición inicial cercana (x=35, y=35)")
print("-"*70)

config3 = {
    "sigma": 5.0,
    "amplitude": 1.0,
    "threshold": 0.01,
    "initial_pos": [35, 35, 5],
    "name": "closer_initial_position"
}

try:
    traj, odor, actions, dists, metrics = run_working_simulation(
        config3["sigma"], config3["amplitude"], config3["threshold"],
        config3["initial_pos"], duration=20
    )
    results = save_simulation_data(traj, odor, actions, dists, metrics, config3["name"], experiment_dir)
    all_results["simulations"][config3["name"]] = metrics
except Exception as e:
    print(f"    Error: {e}")


# CONFIGURACIÓN 4: Parámetros optimizados (combinación de amplitud y sigma)
print("\n4. Parámetros optimizados: sigma=15 + initial=(20,20)")
print("-"*70)

config4 = {
    "sigma": 15.0,
    "amplitude": 1.0,
    "threshold": 0.01,
    "initial_pos": [20, 20, 5],
    "name": "optimized_sigma15_near"
}

try:
    traj, odor, actions, dists, metrics = run_working_simulation(
        config4["sigma"], config4["amplitude"], config4["threshold"],
        config4["initial_pos"], duration=30
    )
    results = save_simulation_data(traj, odor, actions, dists, metrics, config4["name"], experiment_dir)
    all_results["simulations"][config4["name"]] = metrics
except Exception as e:
    print(f"    Error: {e}")


# Guardar resumen
summary_file = experiment_dir / "experiment_summary.json"
with open(summary_file, "w") as f:
    json.dump(all_results, f, indent=2)

print("\n" + "="*70)
print(f"✓ EXPERIMENTO COMPLETADO")
print(f"✓ Resultados guarados en: {experiment_dir}/")
print("="*70)

# Análisis comparativo
print("\n" + "="*70)
print("ANÁLISIS COMPARATIVO")
print("="*70)

for sim_name, sim_data in all_results["simulations"].items():
    success = sim_data["results"]["success"]
    improvement = sim_data["results"]["total_improvement"]
    final_dist = sim_data["results"]["final_distance"]
    status = "✓ ÉXITO" if success else "✗ FALLO"
    
    print(f"\n{sim_name}: {status}")
    print(f"  Mejora: {improvement:.1f}mm")
    print(f"  Distancia final: {final_dist:.1f}mm")
    print(f"  % sobre threshold: {sim_data['results']['percent_above_threshold']:.1f}%")
