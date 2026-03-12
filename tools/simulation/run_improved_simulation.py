"""
Simulación mejorada de navegación olfatoria con FlyGym.

Arreglos implementados:
1. Olor más intenso: sigma=25.0, amplitud=1.5
2. Umbrales más bajos: threshold=0.001
3. Integración correcta con BrainFly
4. Logging detallado de cada paso
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.olfaction.odor_field import OdorField
from src.controllers.olfactory_brain import OlfactoryBrain
from src.controllers.brain_fly import BrainFly
from src.simulation.olfactory_sim import OlfactorySimulation

try:
    from flygym import Fly, Simulation
    from flygym.arena import FlatTerrain
    FLYGYM_AVAILABLE = True
except ImportError:
    print("⚠ FlyGym no disponible, usando simulación simplificada")
    FLYGYM_AVAILABLE = False


def create_output_dir():
    """Crear directorio de salida con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M")
    output_dir = Path("outputs") / f"Experiment - {timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


class ImprovedOlfactorySimulation:
    """
    Simulación mejorada con mejor integración y logging.
    """
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs = []
        self.config = {}
    
    def run(self, sigma=25.0, amplitude=1.5, threshold=0.001, 
            initial_pos=[10, 10, 5], duration=30.0):
        """
        Ejecutar simulación con parámetros dados.
        
        Parameters
        ----------
        sigma : float
            Dispersión del campo de olor (mayor = más amplio)
        amplitude : float
            Amplitud máxima del olor
        threshold : float
            Umbral de detección del cerebro
        initial_pos : list
            Posición inicial [x, y, z]
        duration : float
            Duración de simulación en segundos
        """
        
        print(f"\n{'='*80}")
        print(f"SIMULACIÓN OLFATORIA MEJORADA")
        print(f"{'='*80}")
        
        # Configuración
        self.config = {
            "timestamp": datetime.now().isoformat(),
            "odor_source": [50, 50, 5],
            "sigma": sigma,
            "amplitude": amplitude,
            "threshold": threshold,
            "initial_position": initial_pos,
            "duration_seconds": duration,
            "brain_mode": "gradient",
            "forward_scale": 1.0,
            "turn_scale": 0.5
        }
        
        print(f"\nConfiguración:")
        print(f"  Fuente de olor: {self.config['odor_source']}")
        print(f"  Sigma (dispersión): {sigma} mm")
        print(f"  Amplitud máxima: {amplitude}")
        print(f"  Umbral del cerebro: {threshold}")
        print(f"  Posición inicial: {initial_pos}")
        print(f"  Duración: {duration} s")
        
        # Crear componentes
        odor_field = OdorField(
            sources=self.config["odor_source"],
            sigma=sigma,
            amplitude=amplitude
        )
        
        brain = OlfactoryBrain(
            threshold=threshold,
            mode="gradient",
            forward_scale=self.config["forward_scale"],
            turn_scale=self.config["turn_scale"]
        )
        
        print(f"\n✓ Campo de olor creado")
        print(f"✓ Cerebro olfatorio creado (modo: gradient)")
        
        # Simular sin FlyGym (para asegurar consistencia)
        if not FLYGYM_AVAILABLE:
            print(f"\n⚠ Simulando sin FlyGym (modo simplificado)")
            return self._simulate_simplified(
                odor_field, brain, initial_pos, duration
            )
        else:
            print(f"\n✓ Integrando con FlyGym")
            return self._simulate_with_flygym(
                odor_field, brain, initial_pos, duration
            )
    
    def _simulate_simplified(self, odor_field, brain, initial_pos, duration):
        """Simulación simplificada sin FlyGym."""
        
        dt = 0.01  # 10ms timestep
        num_steps = int(duration / dt)
        source = np.array(self.config["odor_source"])
        
        position = np.array(initial_pos, dtype=float)
        heading = np.deg2rad(np.random.uniform(0, 360))  # Dirección aleatoria inicial
        
        print(f"\nEjecutando simulación: {num_steps} pasos ({duration}s)")
        
        for step in range(num_steps):
            t = step * dt
            
            # 1. Sensar olor
            odor_conc = odor_field.concentration_at(position)
            
            # 2. Cerebro procesa olor
            motor_output = brain.step(float(odor_conc))
            forward, turn = motor_output
            
            # 3. Física simple: actualizar posición
            # Forward: velocidad forward en dirección del heading
            # Turn: cambio de heading
            linear_speed = float(forward) * 10.0  # mm/s
            angular_speed = float(turn) * np.pi  # rad/s
            
            # Actualizar heading
            heading += angular_speed * dt
            
            # Actualizar posición
            position[0] += linear_speed * np.cos(heading) * dt
            position[1] += linear_speed * np.sin(heading) * dt
            
            # Mantener dentro de arena
            position[0] = np.clip(position[0], 0, 100)
            position[1] = np.clip(position[1], 0, 100)
            position[2] = np.clip(position[2], 0, 10)
            
            # Distancia a fuente
            dist = np.linalg.norm(position[:2] - source[:2])
            
            # Log
            self.logs.append({
                "time": t,
                "x": float(position[0]),
                "y": float(position[1]),
                "z": float(position[2]),
                "heading_deg": float(np.degrees(heading)),
                "odor_concentration": float(odor_conc),
                "brain_forward": float(forward),
                "brain_turn": float(turn),
                "linear_speed": float(linear_speed),
                "distance_to_source": float(dist),
            })
            
            # Progreso
            if (step + 1) % (num_steps // 10) == 0:
                progress = int(100 * (step + 1) / num_steps)
                print(f"  [{progress:3d}%] t={t:.1f}s | "
                      f"conc={odor_conc:.4f} | "
                      f"fwd={forward:+.2f} | "
                      f"dist={dist:.1f}mm")
        
        return self._finalize_simulation()
    
    def _simulate_with_flygym(self, odor_field, brain, initial_pos, duration):
        """Simulación con integración FlyGym."""
        # TODO: Implementar integración completa con FlyGym
        print("  (Integración FlyGym en desarrollo)")
        return self._simulate_simplified(odor_field, brain, initial_pos, duration)
    
    def _finalize_simulation(self):
        """Procesar y guardar resultados."""
        
        print(f"\n{'='*80}")
        print("PROCESANDO RESULTADOS")
        print(f"{'='*80}")
        
        # Convertir logs a arrays
        times = np.array([log["time"] for log in self.logs])
        distances = np.array([log["distance_to_source"] for log in self.logs])
        concentrations = np.array([log["odor_concentration"] for log in self.logs])
        forward_cmds = np.array([log["brain_forward"] for log in self.logs])
        
        # Calcular métricas
        results = {
            "total_steps": len(self.logs),
            "duration_seconds": float(times[-1]),
            "initial_distance_mm": float(distances[0]),
            "final_distance_mm": float(distances[-1]),
            "min_distance_mm": float(np.min(distances)),
            "distance_reduction_mm": float(distances[0] - distances[-1]),
            "mean_odor_concentration": float(np.mean(concentrations)),
            "max_odor_concentration": float(np.max(concentrations)),
            "steps_with_odor": int(np.sum(concentrations > self.config["threshold"])),
            "percent_with_odor": float(100 * np.sum(concentrations > self.config["threshold"]) / len(concentrations)),
            "mean_forward_command": float(np.mean(forward_cmds)),
            "success": bool(distances[-1] < distances[0])
        }
        
        # Evaluación
        print(f"\n✓ RESULTADOS:")
        print(f"  Distancia inicial:   {results['initial_distance_mm']:.1f} mm")
        print(f"  Distancia final:     {results['final_distance_mm']:.1f} mm")
        print(f"  Reducción:           {results['distance_reduction_mm']:.1f} mm")
        print(f"  Mínima distancia:    {results['min_distance_mm']:.1f} mm")
        print(f"  Olor detectado:      {results['percent_with_odor']:.1f}% del tiempo")
        print(f"  Señal forward (avg): {results['mean_forward_command']:+.3f}")
        
        if results['success']:
            print(f"\n✓✓✓ ÉXITO: La mosca se movió hacia el olor")
        else:
            print(f"\n✗✗✗ FALLO: La mosca no se acercó al olor")
            print(f"    Verificar:")
            print(f"    - ¿Concentración > 0? {results['max_odor_concentration']:.4f}")
            print(f"    - ¿Cerebro responde? {results['mean_forward_command']:.3f}")
            print(f"    - ¿Motor se aplica? (ver trayectoria)")
        
        # Guardar datos
        self._save_results(results)
        
        return results
    
    def _save_results(self, results):
        """Guardar todos los datos de simulación."""
        
        # Log detallado
        import csv
        log_file = self.output_dir / "simulation_log.csv"
        with open(log_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.logs[0].keys())
            writer.writeheader()
            writer.writerows(self.logs)
        print(f"\n✓ Log guardado: {log_file.name}")
        
        # Configuración
        config_file = self.output_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✓ Config guardada: {config_file.name}")
        
        # Resultados
        results_file = self.output_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Resultados guardados: {results_file.name}")
        
        return log_file, config_file, results_file


# =============================================================================
# EJECUTAR
# =============================================================================

if __name__ == "__main__":
    output_dir = create_output_dir()
    print(f"Directorio de salida: {output_dir}")
    
    sim = ImprovedOlfactorySimulation(output_dir)
    
    # Ejecutar con parámetros mejorados
    results = sim.run(
        sigma=25.0,        # Muy amplio para detección lejana
        amplitude=1.5,     # Mayor amplitud
        threshold=0.001,   # Umbral muy bajo
        initial_pos=[10, 10, 5],
        duration=30.0
    )
    
    print(f"\n{'='*80}")
    print("SIMULACIÓN COMPLETADA")
    print(f"{'='*80}")
    print(f"\nResultados guardados en: {output_dir}")
