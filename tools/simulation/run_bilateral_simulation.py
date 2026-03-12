"""
Simulación FINAL de navegación olfatoria con quimiotaxis bilateral REAL.

Implementa verdadera navegación quimiotáctica:
- Sensado bilateral (izquierda/derecha)
- Comparación de gradiente
- Giro orientado hacia mayor concentración
- Movimiento forward proporcional a olor
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
import csv
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.olfaction.odor_field import OdorField
from src.controllers.improved_olfactory_brain import ImprovedOlfactoryBrain


class FinalOlfactorySimulation:
    """Simulación con quimiotaxis bilateral verdadera."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs = []
        self.config = {}
    
    def run(self, sigma=25.0, amplitude=1.5, bilateral_dist=2.0,
            initial_pos=[10, 10, 5], duration=30.0):
        """Ejecutar simulación con quimiotaxis bilateral."""
        
        print(f"\n{'='*80}")
        print("SIMULACIÓN CON QUIMIOTAXIS BILATERAL REAL")
        print(f"{'='*80}")
        
        # Configuración
        self.config = {
            "timestamp": datetime.now().isoformat(),
            "odor_source": [50, 50, 5],
            "sigma": sigma,
            "amplitude": amplitude,
            "bilateral_distance_mm": bilateral_dist,
            "initial_position": initial_pos,
            "duration_seconds": duration,
            "brain_type": "improved_bilateral",
        }
        
        print(f"\nConfiguración:")
        print(f"  Fuente de olor: {self.config['odor_source']}")
        print(f"  Sigma: {sigma} mm")
        print(f"  Amplitud: {amplitude}")
        print(f"  Distancia bilateral: {bilateral_dist} mm")
        print(f"  Posicion inicial: {initial_pos}")
        print(f"  Duración: {duration} s")
        
        # Crear campo de olor
        odor_field = OdorField(
            sources=self.config["odor_source"],
            sigma=sigma,
            amplitude=amplitude
        )
        
        # Crear cerebro mejorado
        brain = ImprovedOlfactoryBrain(
            bilateral_distance=bilateral_dist,
            forward_scale=1.0,
            turn_scale=1.0,
            threshold=0.0001
        )
        
        print(f"\n✓ Campo de olor creado (σ={sigma}mm, A={amplitude})")
        print(f"✓ Cerebro bilateral creado")
        
        # Simulación
        dt = 0.01  # 10ms timestep
        num_steps = int(duration / dt)
        source = np.array(self.config["odor_source"])
        
        position = np.array(initial_pos, dtype=float)
        heading = 0.0  # Radianes
        velocity = 0.0
        angular_velocity = 0.0
        
        print(f"\nEjecutando simulación: {num_steps} pasos ({duration}s)")
        
        for step in range(num_steps):
            t = step * dt
            
            # Cerebro: leer gradiente bilateral y generar comandos
            motor_output = brain.step(odor_field, position, heading)
            forward_cmd, turn_cmd = motor_output
            
            # Dinámica de movimiento
            # Velocidad forward actual basada en comando
            target_velocity = float(forward_cmd) * 20.0  # mm/s máximo
            velocity = 0.9 * velocity + 0.1 * target_velocity  # Suavizar
            
            # Velocidad angular basada en comando de giro
            target_angular = float(turn_cmd) * np.pi  # rad/s máximo
            angular_velocity = 0.9 * angular_velocity + 0.1 * target_angular
            
            # Actualizar heading
            heading += angular_velocity * dt
            heading = heading % (2 * np.pi)  # Normalizar a [0, 2π]
            
            # Actualizar posición
            position[0] += velocity * np.cos(heading) * dt
            position[1] += velocity * np.sin(heading) * dt
            
            # Mantener dentro de arena
            position[0] = np.clip(position[0], 0, 100)
            position[1] = np.clip(position[1], 0, 100)
            position[2] = np.clip(position[2], 0, 10)
            
            # Distancia a fuente
            dist = np.linalg.norm(position[:2] - source[:2])
            
            # Concentración en posición actual
            conc = odor_field.concentration_at(position)
            
            # Log
            self.logs.append({
                "time": t,
                "x": float(position[0]),
                "y": float(position[1]),
                "z": float(position[2]),
                "heading_deg": float(np.degrees(heading)),
                "odor_concentration": float(conc),
                "brain_forward": float(forward_cmd),
                "brain_turn": float(turn_cmd),
                "velocity_mms": float(velocity),
                "angular_velocity_rads": float(angular_velocity),
                "distance_to_source": float(dist),
            })
            
            # Progreso
            if (step + 1) % (num_steps // 10) == 0:
                progress = int(100 * (step + 1) / num_steps)
                print(f"  [{progress:3d}%] t={t:5.1f}s | "
                      f"conc={conc:7.4f} | "
                      f"dist={dist:6.1f}mm | "
                      f"vel={velocity:6.1f}mm/s | "
                      f"turn={turn_cmd:+.2f}")
        
        return self._finalize(odor_field)
    
    def _finalize(self, odor_field):
        """Procesar resultados."""
        
        print(f"\n{'='*80}")
        print("ANÁLISIS DE RESULTADOS")
        print(f"{'='*80}")
        
        times = np.array([log["time"] for log in self.logs])
        distances = np.array([log["distance_to_source"] for log in self.logs])
        concentrations = np.array([log["odor_concentration"] for log in self.logs])
        forward_cmds = np.array([log["brain_forward"] for log in self.logs])
        turn_cmds = np.array([log["brain_turn"] for log in self.logs])
        
        # Análisis de fases
        third = len(self.logs) // 3
        early_distances = distances[:third]
        late_distances = distances[2*third:]
        
        results = {
            "duration": float(times[-1]),
            "initial_distance_mm": float(distances[0]),
            "final_distance_mm": float(distances[-1]),
            "min_distance_mm": float(np.min(distances)),
            "max_distance_mm": float(np.max(distances)),
            "distance_reduction_mm": float(distances[0] - distances[-1]),
            "distance_reduction_percent": float(100 * (distances[0] - distances[-1]) / distances[0]),
            "mean_distance_early_mm": float(np.mean(early_distances)),
            "mean_distance_late_mm": float(np.mean(late_distances)),
            "mean_odor_concentration": float(np.mean(concentrations)),
            "max_odor_concentration": float(np.max(concentrations)),
            "mean_forward_command": float(np.mean(forward_cmds)),
            "mean_turn_command": float(np.mean(turn_cmds)),
            "success": bool(distances[-1] < distances[0]),
            "progress": bool(np.mean(late_distances) < np.mean(early_distances))
        }
        
        print(f"\n✓ MÉTRICAS:")
        print(f"  Distancia inicial:     {results['initial_distance_mm']:6.1f} mm")
        print(f"  Distancia final:       {results['final_distance_mm']:6.1f} mm")
        print(f"  Reducción:             {results['distance_reduction_mm']:6.1f} mm ({results['distance_reduction_percent']:5.1f}%)")
        print(f"  Mínima distancia:      {results['min_distance_mm']:6.1f} mm")
        print(f"\n✓ COMPORTAMIENTO:")
        print(f"  Olor max detectado:    {results['max_odor_concentration']:7.4f}")
        print(f"  Olor promedio:         {results['mean_odor_concentration']:7.4f}")
        print(f"  Señal forward (avg):   {results['mean_forward_command']:+.3f}")
        print(f"  Señal giro (avg):      {results['mean_turn_command']:+.3f}")
        print(f"\n✓ EVALUACIÓN:")
        print(f"  Progreso temprano→tarde: {'SÍ ✓' if results['progress'] else 'NO ✗'}")
        print(f"  Acercamiento final:      {'SÍ ✓✓✓' if results['success'] else 'NO ✗✗✗'}")
        
        # Guardar
        self._save(results, odor_field)
        
        return results
    
    def _save(self, results, odor_field):
        """Guardar resultados."""
        
        # CSV de trayectoria
        csv_file = self.output_dir / "trajectory.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.logs[0].keys())
            writer.writeheader()
            writer.writerows(self.logs)
        print(f"\n✓ Trayectoria: {csv_file.name}")
        
        # JSON de configuración
        config_file = self.output_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✓ Config: {config_file.name}")
        
        # JSON de resultados
        results_file = self.output_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Resultados: {results_file.name}")


# =============================================================================
# EJECUTAR
# =============================================================================

if __name__ == "__main__":
    output_dir = Path("outputs") / f"Experiment - {datetime.now().strftime('%Y-%m-%d_%H_%M')}"
    
    sim = FinalOlfactorySimulation(output_dir)
    results = sim.run(
        sigma=25.0,
        amplitude=1.5,
        bilateral_dist=2.0,  # 2mm entre sensores simulados
        initial_pos=[10, 10, 5],
        duration=30.0
    )
    
    print(f"\n{'='*80}")
    print(f"Resultados guardados en: {output_dir}")
    print(f"{'='*80}\n")
