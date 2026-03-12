#!/usr/bin/env python3
"""
Ejecutor modular de simulaciones olfatorias.

Solo corre la simulación y guarda los datos brutos en CSV/JSON.
NO incluye validación ni renderizado - estos son pasos separados.

Este módulo es independiente e agnóstico al motor de física usado.
"""

import sys
import numpy as np
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List, Optional, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class SimulationRunner:
    """
    Ejecuta una simulación olfatoria y guarda datos crudos.
    
    Características:
    - Crea timestamped output folders automáticamente
    - Soporta FlyGym (física real) o fallback (cinemática simple)
    - Logging completo de trayectoria, olor, comandos motores
    - Independiente de validación/renderizado
    """
    
    def __init__(
        self,
        output_base_dir: str = "outputs/simulations",
        sim_type: str = "kinematic",
        verbose: bool = True
    ):
        """
        Inicializar el ejecutor.
        
        Args:
            output_base_dir: Directorio base para outputs (se crea timestamp automáticamente)
            sim_type: "kinematic" para cinemática simple, "mujoco" para FlyGym
            verbose: Imprimir progreso
        """
        self.output_base_dir = Path(output_base_dir)
        self.sim_type = sim_type
        self.verbose = verbose
        
        # Directorio timestamped (se crea en run())
        self.sim_dir = None
        
        # Logs
        self.trajectory_data = []
        self.times = []
        self.positions = []
        self.odor_concs = []
        self.motor_commands = []
    
    def _create_output_dir(self) -> Path:
        """Crear directorio timestamped para outputs."""
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        sim_dir = self.output_base_dir / timestamp
        sim_dir.mkdir(parents=True, exist_ok=True)
        return sim_dir
    
    def run(
        self,
        odor_field,
        brain,
        duration: float = 10.0,
        arena_size: Tuple[float, float, float] = (100, 100, 10),
        source_pos: Tuple[float, float, float] = (50, 50, 5),
        dt: float = 0.01,
        **kwargs
    ) -> Path:
        """
        Ejecutar la simulación.
        
        Args:
            odor_field: OdorField instance
            brain: OlfactoryBrain instance
            duration: Duración en segundos
            arena_size: Tamaño arena (x, y, z) en mm
            source_pos: Posición fuente (x, y, z) en mm
            dt: Timestep control
            **kwargs: Argumentos adicionales
        
        Returns:
            Path al directorio de output
        """
        # Crear directorio
        self.sim_dir = self._create_output_dir()
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"SIMULATION RUNNER - {self.sim_type.upper()}")
            print(f"{'='*70}")
            print(f"Output: {self.sim_dir}")
            print(f"Duration: {duration}s")
            print(f"Type: {self.sim_type}")
        
        # Ejecutar según tipo
        if self.sim_type == "kinematic":
            self._run_kinematic(odor_field, brain, duration, arena_size, source_pos, dt)
        elif self.sim_type == "mujoco":
            self._run_mujoco(odor_field, brain, duration, arena_size, source_pos, dt)
        else:
            raise ValueError(f"Unknown sim_type: {self.sim_type}")
        
        # Guardar datos
        self._save_trajectory(source_pos)
        self._save_config(odor_field, brain, duration, arena_size, source_pos)
        
        if self.verbose:
            print(f"\n✓ Simulación completada: {len(self.times)} timesteps")
            print(f"✓ Output guardado en: {self.sim_dir}\n")
        
        return self.sim_dir
    
    def _run_kinematic(
        self,
        odor_field,
        brain,
        duration: float,
        arena_size: Tuple,
        source_pos: Tuple,
        dt: float
    ):
        """Ejecutar simulación cinemática simple."""
        
        if self.verbose:
            print(f"\nUsando simulación cinemática (sin física real)...")
        
        # Importar simulador simple
        try:
            from simple_olfactory_sim import SimpleOlfactorySim
            sim = SimpleOlfactorySim(odor_field, brain, source_pos, arena_size)
        except ImportError:
            # Fallback: implementación inline
            sim = self._create_fallback_sim(odor_field, brain, source_pos, arena_size)
        
        # Simulation loop
        n_steps = int(duration / dt)
        for step in range(n_steps):
            if self.verbose and step % max(1, n_steps // 10) == 0:
                print(f"  Step {step}/{n_steps}...")
            
            # Ejecutar paso
            conc = sim.step(dt)
            
            # Log
            self.times.append(step * dt)
            self.positions.append(sim.pos.copy())
            self.odor_concs.append(conc)
            
            if hasattr(sim, 'last_motor_command'):
                self.motor_commands.append(sim.last_motor_command.copy())
    
    def _run_mujoco(
        self,
        odor_field,
        brain,
        duration: float,
        arena_size: Tuple,
        source_pos: Tuple,
        dt: float
    ):
        """Ejecutar simulación con FlyGym/MuJoCo."""
        
        if self.verbose:
            print(f"\nIntentando usar FlyGym para simulación con física real...")
        
        try:
            from flygym import Fly, Simulation
            from flygym.arena import FlatTerrain
        except ImportError:
            if self.verbose:
                print(f"  ⚠ FlyGym no disponible, usando fallback cinemático...")
            self._run_kinematic(odor_field, brain, duration, arena_size, source_pos, dt)
            return
        
        try:
            # Crear entorno FlyGym
            fly = Fly(enable_adhesion=True, enable_joint_sensors=True)
            arena = FlatTerrain()
            
            sim = Simulation(
                fly=fly,
                arena=arena,
                physics_timestep=dt,
                render_playspeed=1,
                render_interval=100,
            )
            
            if self.verbose:
                print(f"  ✓ FlyGym inicializado")
            
            # Reset
            obs, info = sim.reset()
            
            # Simulation loop
            n_steps = int(duration / dt)
            for step in range(n_steps):
                if self.verbose and step % max(1, n_steps // 10) == 0:
                    print(f"  Step {step}/{n_steps}...")
                
                # Get fly state
                try:
                    fly_state = obs.get("Fly")[0] if isinstance(obs.get("Fly"), (list, tuple)) else obs.get("Fly", {})
                    pos = np.array(fly_state.get("head_position", [0, 0, 0]))
                except:
                    pos = np.array([0, 0, 0])
                
                # Get heading
                try:
                    heading = np.array(fly_state.get("heading", [1, 0, 0]))
                    heading_angle = np.arctan2(heading[1], heading[0])
                except:
                    heading_angle = 0
                
                # Brain step
                motor_cmd = brain.step(odor_field, pos, heading_angle)
                forward, turn = motor_cmd
                
                # Execute in FlyGym
                try:
                    action = {"Fly": np.array([forward, turn])}
                    obs, _, terminated, truncated, _ = sim.step(action)
                except:
                    # Fallback action format
                    action = np.array([forward, turn])
                    obs, _, terminated, truncated, _ = sim.step(action)
                
                # Log
                conc = float(odor_field.concentration_at(pos))
                self.times.append(step * dt)
                self.positions.append(pos.copy())
                self.odor_concs.append(conc)
                self.motor_commands.append([forward, turn])
                
                if terminated or truncated:
                    if self.verbose:
                        print(f"  Simulación terminada en step {step}")
                    break
        
        except Exception as e:
            if self.verbose:
                print(f"  ✗ Error en FlyGym: {e}")
                print(f"  Usando fallback cinemático...")
            self._run_kinematic(odor_field, brain, duration, arena_size, source_pos, dt)
    
    def _create_fallback_sim(self, odor_field, brain, source_pos, arena_size):
        """
        Crear simulador cinemático fallback inline.
        Implementación mínima si SimpleOlfactorySim no está disponible.
        """
        class FallbackSim:
            def __init__(self, odor_field, brain, source_pos, arena_size):
                self.odor_field = odor_field
                self.brain = brain
                self.source_pos = np.array(source_pos[:2])
                self.arena_size = arena_size
                
                # Posición inicial: centro arena, alejada de fuente
                self.pos = np.array([arena_size[0]/2, arena_size[1]/2, 0.0])
                self.heading = 0.0  # radianes
                self.last_motor_command = [0, 0]
            
            def step(self, dt):
                # Obtener concentración
                conc = float(self.odor_field.concentration_at(self.pos[:2]))
                
                # Brain decision
                motor = self.brain.step(self.odor_field, self.pos, self.heading)
                forward, turn = motor
                self.last_motor_command = [forward, turn]
                
                # Kinematic update
                self.heading += turn * dt * 5  # 5 rad/s * turn scale
                vel_x = forward * 10 * dt  # forward scale = 10 mm/s
                vel_y = 0
                
                # Update position
                self.pos[0] += vel_x * np.cos(self.heading)
                self.pos[1] += vel_x * np.sin(self.heading)
                
                # Clamp a arena
                self.pos[0] = np.clip(self.pos[0], 0, self.arena_size[0])
                self.pos[1] = np.clip(self.pos[1], 0, self.arena_size[1])
                
                return conc
        
        return FallbackSim(odor_field, brain, source_pos, arena_size)
    
    def _save_trajectory(self, source_pos: Tuple):
        """Guardar trayectoria a CSV."""
        csv_path = self.sim_dir / "trajectory.csv"
        
        with open(csv_path, 'w', newline='') as f:
            fieldnames = ['timestamp', 'x', 'y', 'z', 'odor_concentration', 'distance_to_source']
            if self.motor_commands:
                fieldnames.extend(['brain_forward', 'brain_turn'])
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, (t, pos, conc) in enumerate(zip(self.times, self.positions, self.odor_concs)):
                row = {
                    'timestamp': t,
                    'x': pos[0],
                    'y': pos[1],
                    'z': pos[2] if len(pos) > 2 else 0,
                    'odor_concentration': conc,
                    'distance_to_source': np.linalg.norm(pos[:2] - np.array(source_pos[:2])),
                }
                
                if self.motor_commands and i < len(self.motor_commands):
                    row['brain_forward'] = self.motor_commands[i][0]
                    row['brain_turn'] = self.motor_commands[i][1]
                
                writer.writerow(row)
        
        if self.verbose:
            print(f"\n✓ Trayectoria guardada: {csv_path}")
    
    def _save_config(self, odor_field, brain, duration, arena_size, source_pos):
        """Guardar configuración a JSON."""
        config = {
            "timestamp": datetime.now().isoformat(),
            "sim_type": self.sim_type,
            "duration": duration,
            "total_timesteps": len(self.times),
            "arena_size": arena_size,
            "source_pos": source_pos,
            "odor_field": {
                "sigma": getattr(odor_field, 'sigma', None),
                "amplitude": getattr(odor_field, 'amplitude', 1.0),
            },
            "brain": {
                "type": brain.__class__.__name__,
                "mode": getattr(brain, 'mode', None),
                "threshold": getattr(brain, 'threshold', None),
            },
        }
        
        config_path = self.sim_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        if self.verbose:
            print(f"✓ Configuración guardada: {config_path}")
