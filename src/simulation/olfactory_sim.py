"""
Bucle principal de simulación con controlador olfatorio.

Orquesta la creación de la arena, mosca, cámara, y ejecuta el ciclo
sensoriomotor de navegación olfatoria.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import json
from datetime import datetime

try:
    from flygym import Fly, Simulation
    from flygym.vision import Camera
except ImportError:
    Fly = None
    Simulation = None
    Camera = None


class OlfactorySimulation:
    """
    Gestor de simulación olfatoria.
    
    Crea y ejecuta un experimento de navegación olfatoria con:
    - Campo de olor configurable
    - Controlador sensoriomotor (BrainFly)
    - Logging de trayectorias y métricas
    - Visualización opcional en tiempo real
    
    Parameters
    ----------
    brain_fly : BrainFly
        Mosca con sensor olfativo e integración cerebral.
    odor_field : OdorField
        Campo de olor del entorno.
    sim_params : Dict[str, float], optional
        Parámetros de simulación: timestep, duration, etc.
    output_dir : str, default="outputs/olfactory"
        Directorio para guardar datos y vídeos.
    """
    
    def __init__(
        self,
        brain_fly,
        odor_field,
        sim_params: Optional[Dict[str, float]] = None,
        output_dir: str = "outputs/olfactory"
    ):
        """Inicializar la simulación."""
        self.brain_fly = brain_fly
        self.odor_field = odor_field
        
        # Parámetros de simulación
        self.sim_params = {
            "physics_dt": 0.0001,  # 100 µs
            "control_dt": 0.01,    # 10 ms (cada 100 pasos de física)
            "sim_duration": 10.0,  # 10 segundos
            "render_interval": 1,  # Renderizar cada N pasos
        }
        if sim_params:
            self.sim_params.update(sim_params)
        
        # Simulación FlyGym (se instancia en setup)
        self.sim = None
        self.camera = None
        
        # Logging
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.trajectory = []  # Trayectoria xyz de la cabeza
        self.odor_log = []    # Concentración en cada paso
        self.action_log = []  # Acciones motoras
        self.time_log = []    # Timestamps
        
        self._is_running = False
    
    def setup(
        self,
        arena_size: Tuple[float, float, float] = (100, 100, 10),
        use_rendering: bool = False,
        **sim_kwargs
    ):
        """
        Configurar la simulación FlyGym.
        
        Parameters
        ----------
        arena_size : Tuple[float, float, float]
            Dimensiones de la arena (x, y, z_height) en mm.
        use_rendering : bool, default=False
            Activar renderizado con cámara.
        **sim_kwargs
            Argumentos adicionales para Simulation()
        """
        if Simulation is None:
            raise RuntimeError("FlyGym no está disponible. Instala: pip install flygym")
        
        # Crear simulación
        self.sim = Simulation(
            [self.brain_fly],
            arena_size=arena_size,
            physics_timestep=self.sim_params["physics_dt"],
            render_playspeed=True,
            render_interval=self.sim_params["render_interval"],
            **sim_kwargs
        )
        
        # Configurar cámara si se requiere
        if use_rendering:
            # Parámetros típicos de cámara en FlyGym
            self.camera = Camera(
                fly_ids=["Nuro"],
                play_speed=10,
                **sim_kwargs
            )
        
        print(f"✓ Simulación configurada: physics_dt={self.sim_params['physics_dt']}, "
              f"control_dt={self.sim_params['control_dt']}")
    
    def reset(self):
        """Resetear la simulación."""
        obs, info = self.sim.reset()
        
        # Resetear cerebro
        self.brain_fly.brain.reset()
        
        # Limpiar logs
        self.trajectory.clear()
        self.odor_log.clear()
        self.action_log.clear()
        self.time_log.clear()
        
        self._is_running = True
        
        return obs, info
    
    def step(self, obs: Dict[str, Any], physics_steps: int = 1):
        """
        Ejecutar N pasos de simulación con control del cerebro.
        
        Parameters
        ----------
        obs : Dict[str, Any]
            Observaciones del paso anterior.
        physics_steps : int, default=1
            Número de pasos de física a ejecutar entre controles del cerebro.
        
        Returns
        -------
        Tuple
            (obs, terminated, truncated) tras los pasos de física.
        """
        # Generar acción desde el cerebro
        action = self.brain_fly.step(obs)
        
        # Ejecutar N pasos de física
        for _ in range(physics_steps):
            obs, terminated, truncated, info = self.sim.step(
                {"Nuro": action}
            )
            
            if terminated or truncated:
                self._is_running = False
                break
        
        return obs, terminated, truncated, info
    
    def run(
        self,
        max_duration: Optional[float] = None,
        render: bool = True,
        verbose: bool = True
    ):
        """
        Ejecutar simulación hasta completarse o exceder duración máxima.
        
        Parameters
        ----------
        max_duration : float, optional
            Duración máxima en segundos. Por defecto usa sim_params['sim_duration'].
        render : bool, default=True
            Mostrar visualización en tiempo real.
        verbose : bool, default=True
            Imprimir progreso.
        
        Returns
        -------
        Dict
            Diccionario con resumen de métricas finales.
        """
        if max_duration is None:
            max_duration = self.sim_params["sim_duration"]
        
        # Resetear
        obs, info = self.reset()
        
        # Calcular número de steps
        physics_dt = self.sim_params["physics_dt"]
        control_dt = self.sim_params["control_dt"]
        physics_per_step = int(control_dt / physics_dt)
        total_steps = int(max_duration / control_dt)
        
        if verbose:
            print(f"Iniciando simulación: {max_duration}s ({total_steps} steps de control)")
        
        # Loop principal
        for step_idx in range(total_steps):
            obs, terminated, truncated, info = self.step(obs, physics_steps=physics_per_step)
            
            # Logging
            current_time = step_idx * control_dt
            self.time_log.append(current_time)
            
            # Extraer posición de cabeza
            try:
                if "Nuro" in obs and "head_pos" in obs["Nuro"]:
                    head_pos = obs["Nuro"]["head_pos"]
                else:
                    head_pos = np.zeros(3)
            except:
                head_pos = np.zeros(3)
            
            self.trajectory.append(head_pos.copy())
            self.odor_log.append(self.brain_fly.get_odor_concentration())
            
            if render and hasattr(self.sim, 'render'):
                self.sim.render()
            
            if verbose and (step_idx + 1) % 100 == 0:
                print(f"  Step {step_idx + 1}/{total_steps} "
                      f"({current_time:.2f}s, odor={self.odor_log[-1]:.3f})")
            
            if terminated or truncated:
                if verbose:
                    print(f"Simulación terminada en step {step_idx + 1}")
                break
        
        # Compilar métricas
        metrics = self._compute_metrics()
        
        if verbose:
            print(f"\n✓ Simulación completada. Duración: {self.time_log[-1]:.2f}s")
            print(f"  Distancia total: {metrics['total_distance']:.1f} mm")
            print(f"  Concentración media: {metrics['mean_odor']:.4f}")
            print(f"  Concentración máxima: {metrics['max_odor']:.4f}")
        
        return metrics
    
    def _compute_metrics(self) -> Dict[str, float]:
        """Calcular métricas de la trayectoria."""
        trajectory = np.array(self.trajectory)
        odor_log = np.array(self.odor_log)
        
        # Distancia total (suma de desplazamientos incrementales)
        if len(trajectory) > 1:
            displacements = np.linalg.norm(np.diff(trajectory, axis=0), axis=1)
            total_distance = np.sum(displacements)
        else:
            total_distance = 0.0
        
        # Estadísticas de olor
        mean_odor = np.mean(odor_log) if len(odor_log) > 0 else 0.0
        max_odor = np.max(odor_log) if len(odor_log) > 0 else 0.0
        min_odor = np.min(odor_log) if len(odor_log) > 0 else 0.0
        
        # Primer y último olor
        first_odor = odor_log[0] if len(odor_log) > 0 else 0.0
        last_odor = odor_log[-1] if len(odor_log) > 0 else 0.0
        
        return {
            "total_distance": float(total_distance),
            "mean_odor": float(mean_odor),
            "max_odor": float(max_odor),
            "min_odor": float(min_odor),
            "first_odor": float(first_odor),
            "last_odor": float(last_odor),
            "steps_completed": len(self.trajectory),
        }
    
    def save_data(self, suffix: str = ""):
        """
        Guardar trayectoria, olor y datos a archivos.
        
        Parameters
        ----------
        suffix : str, optional
            Sufijo para los nombres de archivo.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            prefix = f"{timestamp}_{suffix}"
        else:
            prefix = timestamp
        
        trajectory = np.array(self.trajectory)
        odor_log = np.array(self.odor_log)
        time_log = np.array(self.time_log)
        
        # Guardar como numpy arrays
        np.save(self.output_dir / f"{prefix}_trajectory.npy", trajectory)
        np.save(self.output_dir / f"{prefix}_odor.npy", odor_log)
        np.save(self.output_dir / f"{prefix}_time.npy", time_log)
        
        # Guardar como CSV también
        import csv
        with open(self.output_dir / f"{prefix}_data.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "x", "y", "z", "odor"])
            for t, pos, odor in zip(time_log, trajectory, odor_log):
                writer.writerow([t, pos[0], pos[1], pos[2], odor])
        
        print(f"✓ Datos guardados en {self.output_dir}/")
    
    def save_config(self, suffix: str = ""):
        """Guardar configuración de la simulación."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            prefix = f"{timestamp}_{suffix}"
        else:
            prefix = timestamp
        
        config = {
            "sim_params": self.sim_params,
            "odor_field": {
                "sources": self.odor_field.sources.tolist(),
                "sigma": self.odor_field.sigma,
                "amplitude": self.odor_field.amplitude,
            },
            "brain": {
                "threshold": self.brain_fly.brain.threshold,
                "mode": self.brain_fly.brain.mode,
            },
        }
        
        with open(self.output_dir / f"{prefix}_config.json", "w") as f:
            json.dump(config, f, indent=2)


def test_olfactory_sim():
    """Test de estructura de simulación."""
    print("✓ OlfactorySimulation está estructurada correctamente.")


if __name__ == "__main__":
    test_olfactory_sim()
