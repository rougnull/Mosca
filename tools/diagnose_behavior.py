"""
Script de diagnóstico para el comportamiento olfatorio.

Analiza datos brutos de simulación para identificar problemas
sin generar gráficos innecesarios.
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
from datetime import datetime

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain


class BehaviorDiagnostics:
    """Diagnosticar problemas en el comportamiento olfatorio."""
    
    def __init__(self, output_dir="outputs"):
        self.output_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M")
        self.experiment_dir = self.output_dir / f"Experiment - {self.timestamp}"
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def test_odor_field(self, source=(50, 50, 5), sigma=15.0):
        """
        Evaluar el campo de olor en varios puntos.
        
        Returns
        -------
        dict : Métricas del campo de olor
        """
        print("\n" + "="*70)
        print("TEST 1: Campo de Olor (Odor Field)")
        print("="*70)
        
        odor_field = OdorField(sources=source, sigma=sigma, amplitude=1.0)
        
        # Evaluar en puntos clave
        test_points = {
            "En la fonte": source,
            "1mm de fuente": (source[0] + 1, source[1], source[2]),
            "5mm de fuente": (source[0] + 5, source[1], source[2]),
            "10mm de fuente": (source[0] + 10, source[1], source[2]),
            "20mm de fuente": (source[0] + 20, source[1], source[2]),
            "30mm de fuente": (source[0] + 30, source[1], source[2]),
            "Esquina opuesta": (10, 10, 5),
        }
        
        field_metrics = {}
        for label, point in test_points.items():
            conc = odor_field.concentration_at(np.array(point))
            field_metrics[label] = float(conc)
            print(f"  {label:30s}: {conc:.6f}")
        
        # Evaluar campo en rejilla
        grid_points = []
        for x in np.linspace(10, 90, 9):
            for y in np.linspace(10, 90, 9):
                grid_points.append([x, y, 5.0])
        
        grid_conc = odor_field.concentration_at(np.array(grid_points))
        
        field_stats = {
            "sigma": sigma,
            "source": source,
            "amplitude": 1.0,
            "sample_points": field_metrics,
            "grid_stats": {
                "mean_concentration": float(np.mean(grid_conc)),
                "max_concentration": float(np.max(grid_conc)),
                "min_concentration": float(np.min(grid_conc)),
                "std_concentration": float(np.std(grid_conc)),
                "percentile_90": float(np.percentile(grid_conc, 90)),
                "percentile_50": float(np.percentile(grid_conc, 50)),
                "percentile_10": float(np.percentile(grid_conc, 10)),
            }
        }
        
        print(f"\n  Estadísticas en rejilla (9x9):")
        print(f"    Media: {field_stats['grid_stats']['mean_concentration']:.6f}")
        print(f"    Máximo: {field_stats['grid_stats']['max_concentration']:.6f}")
        print(f"    P90: {field_stats['grid_stats']['percentile_90']:.6f}")
        print(f"    P10: {field_stats['grid_stats']['percentile_10']:.6f}")
        
        return field_stats
    
    def test_threshold_vs_field(self, field_stats, thresholds=[0.01, 0.05, 0.1, 0.15, 0.2]):
        """
        Diagnosticar si el threshold es compatible con el campo de olor.
        
        Returns
        -------
        dict : Análisis de compatibilidad threshold/field
        """
        print("\n" + "="*70)
        print("TEST 2: Compatibilidad Threshold vs Campo de Olor")
        print("="*70)
        
        max_conc = field_stats['grid_stats']['max_concentration']
        
        print(f"  Concentración máxima en el campo: {max_conc:.6f}")
        print(f"\n  Análisis de thresholds:")
        
        analysis = {}
        for threshold in thresholds:
            ratio = max_conc / threshold if threshold > 0 else float('inf')
            detectable = max_conc > threshold * 1.1  # 10% tolerancia
            
            analysis[threshold] = {
                "max_concentration": max_conc,
                "threshold": threshold,
                "ratio": ratio,
                "detectable": detectable,
                "recommendation": "✓ VIABLE" if detectable else "✗ TOO HIGH"
            }
            
            status = "✓ VIABLE" if detectable else "✗ TOO HIGH"
            print(f"    Threshold={threshold:.3f}: max/threshold={ratio:.1f}x → {status}")
        
        return analysis
    
    def simulate_trajectory(
        self,
        odor_source=(50, 50, 5),
        brain_mode="gradient",
        threshold=0.01,  # Reducido de 0.1
        sigma=5.0,  # Reducido de 15.0
        duration_seconds=10,
    ):
        """
        Ejecutar simulación de navegación y recolectar datos brutos.
        
        Returns
        -------
        dict : Datos de trayectoria y métricas
        """
        print("\n" + "="*70)
        print(f"TEST 3: Simulación de Navegación")
        print(f"  Modo: {brain_mode}")
        print(f"  Threshold: {threshold:.4f}")
        print(f"  Sigma: {sigma:.1f}")
        print("="*70)
        
        # Parámetros
        dt = 0.01  # 10 ms
        num_steps = int(duration_seconds / dt)
        max_speed = 10  # mm/s
        max_angular_speed = 90  # deg/s
        
        # Crear campo y cerebro
        odor_field = OdorField(sources=odor_source, sigma=sigma, amplitude=1.0)
        brain = OlfactoryBrain(
            threshold=threshold,
            mode=brain_mode,
            forward_scale=1.0,
            turn_scale=1.0
        )
        
        # Inicializar
        position = np.array([10.0, 10.0, 5.0])
        heading = 0.0
        
        # Logs
        trajectory = []
        odor_readings = []
        motor_outputs = []
        distances_to_source = []
        
        # Simulación
        for step in range(num_steps):
            # Sensor
            conc = odor_field.concentration_at(position)
            odor_readings.append(conc)
            
            # Cerebro
            action = brain.step(conc)  # [forward, turn]
            motor_outputs.append(action)
            
            # Actuadores
            heading += np.deg2rad(action[1] * max_angular_speed * dt)
            velocity = max_speed * action[0]
            delta_pos = np.array([
                velocity * np.cos(heading) * dt,
                velocity * np.sin(heading) * dt,
                0
            ])
            position = position + delta_pos
            
            # Limites arena
            position[0] = np.clip(position[0], 0, 100)
            position[1] = np.clip(position[1], 0, 100)
            
            # Log
            trajectory.append(position.copy())
            dist = np.linalg.norm(position[:2] - np.array(odor_source)[:2])
            distances_to_source.append(dist)
            
            if (step + 1) % 500 == 0:
                print(f"  Step {step + 1}/{num_steps}: "
                      f"conc={conc:.6f}, dist={dist:.1f}mm, forward={action[0]:.2f}, turn={action[1]:.2f}")
        
        trajectory = np.array(trajectory)
        odor_readings = np.array(odor_readings)
        motor_outputs = np.array(motor_outputs)
        distances_to_source = np.array(distances_to_source)
        
        # Métricas
        metrics = {
            "config": {
                "mode": brain_mode,
                "threshold": threshold,
                "sigma": sigma,
                "duration": duration_seconds,
                "arena_size": [100, 100, 10],
                "source": odor_source,
                "timestamp": datetime.now().isoformat()
            },
            "statistics": {
                "n_steps": num_steps,
                "mean_odor": float(np.mean(odor_readings)),
                "max_odor": float(np.max(odor_readings)),
                "min_odor": float(np.min(odor_readings)),
                "std_odor": float(np.std(odor_readings)),
                "n_steps_above_threshold": int(np.sum(odor_readings > threshold)),
                "percent_above_threshold": float(100 * np.sum(odor_readings > threshold) / num_steps),
                "initial_distance": float(distances_to_source[0]),
                "final_distance": float(distances_to_source[-1]),
                "min_distance": float(np.min(distances_to_source)),
                "distance_change": float(distances_to_source[0] - distances_to_source[-1]),
                "mean_forward_command": float(np.mean(motor_outputs[:, 0])),
                "mean_turn_command": float(np.mean(motor_outputs[:, 1])),
            }
        }
        
        print(f"\n  Resultados:")
        print(f"    Concentración media: {metrics['statistics']['mean_odor']:.6f}")
        print(f"    Concentración máxima: {metrics['statistics']['max_odor']:.6f}")
        print(f"    % pasos > threshold: {metrics['statistics']['percent_above_threshold']:.1f}%")
        print(f"    Distancia inicial: {metrics['statistics']['initial_distance']:.1f} mm")
        print(f"    Distancia final: {metrics['statistics']['final_distance']:.1f} mm")
        print(f"    Mejora: {metrics['statistics']['distance_change']:.1f} mm")
        
        return trajectory, odor_readings, motor_outputs, distances_to_source, metrics
    
    def save_raw_data(self, trajectory, odor_readings, motor_outputs, distances, metrics, test_name):
        """Guardar datos brutos en CSV para análisis posterior."""
        
        # Crear subdirectorio para este test
        test_dir = self.experiment_dir / test_name
        test_dir.mkdir(exist_ok=True)
        
        # Guardar metrics como JSON
        with open(test_dir / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        
        # Guardar trayectoria en CSV
        trajectory_file = test_dir / "trajectory.csv"
        with open(trajectory_file, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["step", "x_mm", "y_mm", "z_mm", "odor_conc", "forward_cmd", "turn_cmd", "distance_to_source_mm"])
            for i in range(len(trajectory)):
                writer.writerow([
                    i,
                    trajectory[i, 0],
                    trajectory[i, 1],
                    trajectory[i, 2],
                    odor_readings[i],
                    motor_outputs[i, 0],
                    motor_outputs[i, 1],
                    distances[i]
                ])
        
        print(f"  ✓ Datos guardados en: {test_dir}/")
    
    def run_diagnostics(self):
        """Ejecutar suite completa de diagnósticos."""
        print("\n" + "#"*70)
        print("# DIAGNÓSTICO DE COMPORTAMIENTO OLFATORIO")
        print("#"*70)
        
        # Test 1: Campo de olor
        field_stats = self.test_odor_field(source=(50, 50, 5), sigma=5.0)
        
        # Test 2: Threshold compatibility
        thresh_analysis = self.test_threshold_vs_field(field_stats)
        
        # Test 3: Simulaciones con diferentes parámetros
        test_configs = [
            {
                "name": "test_sigma5_threshold001",
                "sigma": 5.0,
                "threshold": 0.001,
                "mode": "gradient"
            },
            {
                "name": "test_sigma5_threshold005",
                "sigma": 5.0,
                "threshold": 0.005,
                "mode": "gradient"
            },
            {
                "name": "test_sigma5_threshold01",
                "sigma": 5.0,
                "threshold": 0.01,
                "mode": "gradient"
            },
            {
                "name": "test_sigma3_threshold005",
                "sigma": 3.0,
                "threshold": 0.005,
                "mode": "gradient"
            },
            {
                "name": "test_sigma3_threshold01",
                "sigma": 3.0,
                "threshold": 0.01,
                "mode": "binary"
            },
        ]
        
        all_results = {
            "timestamp": self.timestamp,
            "field_stats": field_stats,
            "threshold_analysis": thresh_analysis,
            "simulations": {}
        }
        
        for config in test_configs:
            print(f"\n\n>>> Ejecutando: {config['name']}")
            traj, odor, motors, distances, metrics = self.simulate_trajectory(
                brain_mode=config["mode"],
                threshold=config["threshold"],
                sigma=config["sigma"],
                duration_seconds=10
            )
            self.save_raw_data(traj, odor, motors, distances, metrics, config["name"])
            all_results["simulations"][config["name"]] = metrics
        
        # Guardar resumen general
        summary_file = self.experiment_dir / "diagnostics_summary.json"
        with open(summary_file, "w") as f:
            json.dump(all_results, f, indent=2)
        
        print("\n" + "#"*70)
        print(f"# DIAGNÓSTICO COMPLETADO")
        print(f"# Resultados guardados en: {self.experiment_dir}/")
        print("#"*70)
        
        return all_results


if __name__ == "__main__":
    diagnostics = BehaviorDiagnostics()
    results = diagnostics.run_diagnostics()
