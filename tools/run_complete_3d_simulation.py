#!/usr/bin/env python3
"""
Sistema de Simulación 3D Completo con Renderizado MuJoCo
=========================================================

PIPELINE COMPLETO:
1. Simulación de navegación olfatoria (ImprovedOlfactoryBrain + OdorField)
2. Generación de ángulos articulares (motion patterns biológicamente plausibles)
3. Renderizado 3D en FlyGym con MuJoCoRenderer
4. Exportación a video .mp4

USO:
    python tools/run_complete_3d_simulation.py [--duration 15] [--seed 42]

SALIDA:
    - outputs/3d_simulations/NeuroMechFly_3D.mp4  (video 3D principal)
    - outputs/debug/simulation_log.csv  (datos de simulación)
"""

import sys
from pathlib import Path
import numpy as np
import pickle
from datetime import datetime
import argparse

# Try to import tqdm for progress bars (optional)
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = None

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain

# Import components with proper path handling
from core.config import RenderConfig
from core.data import load_kinematic_data, format_joint_data, get_n_frames

# Try to import FlyGym renderer (desde módulo modular)
try:
    from rendering import MuJoCoRenderer  # Importa desde rendering.__init__.py
    HAS_MUJOCO_RENDERER = True
except Exception as e:
    print(f"Warning: Could not import MuJoCoRenderer: {e}")
    HAS_MUJOCO_RENDERER = False
    MuJoCoRenderer = None


class CompleteOlfactorySimulation:
    """
    Simulación completa de navegación olfatoria + renderizado 3D.
    """
    
    def __init__(
        self,
        odor_source=(50.0, 50.0, 5.0),
        odor_sigma=12.0,
        odor_amplitude=1.0,
        start_pos=(20.0, 20.0, 3.0),
        sim_duration=15.0,
        sim_dt=0.01,
        seed=42
    ):
        """
        Inicializar simulación.
        
        Parameters
        ----------
        odor_source : tuple
            Posición de la fuente de olor (x, y, z) en mm
        odor_sigma : float
            Ancho de distribución gaussiana del olor (mm)
        odor_amplitude : float
            Amplitud máxima de concentración en la fuente
        start_pos : tuple
            Posición inicial de la mosca (x, y, z)
        sim_duration : float
            Duración total de la simulación (segundos)
        sim_dt : float
            Timestep de simulación (segundos)
        seed : int
            Semilla para reproducibilidad
        """
        np.random.seed(seed)
        
        # Componentes de simulación
        self.odor_field = OdorField(
            sources=odor_source,
            sigma=odor_sigma,
            amplitude=odor_amplitude  # CRÍTICO: hasta 100-1000 para distancias >40mm
        )
        self.brain = ImprovedOlfactoryBrain(
            bilateral_distance=1.2,
            forward_scale=1.0,
            turn_scale=0.8,
            temporal_gradient_gain=10.0
        )
        
        # Estado de la mosca
        self.pos = np.array(start_pos, dtype=float)
        
        # Orientación inicial: hacia la fuente
        to_source = np.array(odor_source[:2]) - self.pos[:2]
        self.heading = np.arctan2(to_source[1], to_source[0])
        
        # Parámetros cinemáticos
        self.max_forward_speed = 50.0  # mm/s
        self.max_turn_rate = 300.0      # deg/s
        
        # Parámetros de simulación
        self.sim_dt = sim_dt
        self.sim_duration = sim_duration
        self.n_steps = int(sim_duration / sim_dt)
        
        # Logs
        self.times = []
        self.positions = []  # (N, 3)
        self.headings = []   # (N,) en radianes
        self.angles_data = {}  # ángulos articulares por joint
        self.odor_concentrations = []
        self.brain_actions = []
        
        # Inicializar diccionario de ángulos por articulation
        # Patas: LF, LM, LH, RF, RM, RH
        # Articulaciones por pata: Coxa, Coxa_roll, Coxa_yaw, Femur, Femur_roll, Tibia, Tarsus1
        self.legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
        self.joints_per_leg = ["Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"]
        
        for leg in self.legs:
            for joint in self.joints_per_leg:
                key = f"joint_{leg}{joint}"
                self.angles_data[key] = []
        
        # Estado del patrón de marcha (para generar ángulos)
        self.phase = 0.0  # Fase del patrón de marcha (0-1)
        self.phase_frequency = 2.0  # Ciclos por segundo
        
        # Para suavizar ángulos: guardar el valor anterior de cada joint
        self.prev_angles = {}
        for leg in self.legs:
            for joint in self.joints_per_leg:
                key = f"joint_{leg}{joint}"
                self.prev_angles[key] = 0.0
        
        print("\n" + "="*70)
        print("SIMULACION OLFATORIA COMPLETA CON RENDERIZADO 3D")
        print("="*70)
        print(f"Duracion: {sim_duration}s (n_steps={self.n_steps})")
        print(f"Fuente de olor: {odor_source}, sigma={odor_sigma}mm, A={odor_amplitude}")
        print(f"Posicion inicial: {start_pos}")
        print(f"Timestep: {sim_dt}s")
    
    def _generate_joint_angles_for_step(self, step_idx: int, forward_cmd: float, turn_cmd: float) -> dict:
        """
        Generar ángulos articulares para un timestep dado.
        
        CRÍTICO: Los ángulos DEBEN estar modulados por los comandos del cerebro:
        - forward_cmd (0-1): modula amplitud del patrón de marcha
        - turn_cmd (-1 a 1): modula diferencias de fase entre patas izquierda/derecha
        
        Patrón tripod: LF+RH, LM+RM, LH+RF con offsets de fase coordinados
        
        IMPORTANTE: En los primeros frames, los ángulos son pequeños para transición smooth
        desde la postura inicial "stretch".
        
        Args:
            step_idx: Índice del paso actual
            forward_cmd: Comando de movimiento hacia adelante (0-1)
            turn_cmd: Comando de giro (-1 a 1)
        
        Returns:
            dict: Diccionario con ángulos para cada articulación (en radianes)
        """
        # Fase global de ciclo de marcha
        # Aumenta con forward_cmd (más rápido cuanto más rápido se mueva)
        self.phase = (step_idx / max(self.n_steps, 1)) * self.phase_frequency * (0.3 + 0.7 * forward_cmd)
        phase_cycle = (self.phase * 2 * np.pi) % (2 * np.pi)
        
        # CRÍTICO: Rampa suave en los primeros pasos
        # Transición desde ángulos pequeños (stretch) a marcha completa
        ramp_steps = max(30, int(0.1 * self.n_steps))  # 30-100 pasos de rampa
        ramp_factor = min(1.0, step_idx / ramp_steps)
        
        angles = {}
        
        for leg_idx, leg in enumerate(self.legs):
            # MODIFICACIÓN: Offset de fase modulado por turn_cmd
            # Turn positivo: acelera patas derechas, retarda izquierdas
            # Permite que la mosca gire
            is_right_leg = leg.startswith("R")
            turn_factor = turn_cmd * 0.3  # Limitar efecto del giro
            
            if leg in ["LF", "RH"]:
                base_offset = 0.0
            elif leg in ["LM", "RM"]:
                base_offset = 2.0 * np.pi / 3
            else:  # LH, RF
                base_offset = 4.0 * np.pi / 3
            
            # Modificar offset según turn_cmd y si es pata izquierda/derecha
            if is_right_leg:
                phase_offset = base_offset + turn_factor
            else:
                phase_offset = base_offset - turn_factor
            
            adjusted_phase = (phase_cycle + phase_offset) % (2 * np.pi)
            
            # MODIFICACIÓN: Amplitudes moduladas por forward_cmd Y ramp_factor
            # Sin comando forward → movimiento mínima
            # Con forward=1 → movimiento completo
            # Primeros pasos: amplitudes pequeñas para estabilidad
            amplitude_scale = (0.3 + 0.7 * abs(forward_cmd)) * ramp_factor
            
            # Coxa: rotación horizontal
            angles[f"joint_{leg}Coxa"] = 0.3 * amplitude_scale * np.sin(adjusted_phase - np.pi/4)
            angles[f"joint_{leg}Coxa_roll"] = 0.15 * amplitude_scale * np.sin(adjusted_phase)
            angles[f"joint_{leg}Coxa_yaw"] = 0.2 * amplitude_scale * np.sin(adjusted_phase + np.pi/2)
            
            # Femur hace el trabajo principal de levantamiento
            angles[f"joint_{leg}Femur"] = -0.8 + 0.6 * amplitude_scale * np.sin(adjusted_phase)
            angles[f"joint_{leg}Femur_roll"] = 0.1 * amplitude_scale * np.cos(adjusted_phase)
            
            # Tibia extensión/flexión coordinada
            angles[f"joint_{leg}Tibia"] = 1.2 + 0.5 * amplitude_scale * np.cos(adjusted_phase)
            
            # Tarsus pequeñas correcciones
            angles[f"joint_{leg}Tarsus1"] = 0.05 * amplitude_scale * np.sin(adjusted_phase * 2)
        
        return angles
    
    def step(self) -> bool:
        """
        Ejecutar un paso de simulación.
        
        Returns
        -------
        bool
            True si la simulación continúa, False si terminó
        """
        # Sensado olfatorio y decisión del cerebro
        action = self.brain.step(self.odor_field, self.pos, self.heading)
        forward_cmd = float(action[0])
        turn_cmd = float(action[1])
        
        # Obtener concentración actual
        conc = float(self.odor_field.concentration_at(self.pos))
        
        # Cinemática simple (modelos de flujo)
        # Forward: lineal en dirección del heading
        # Turn: cambio angular
        linear_velocity = forward_cmd * self.max_forward_speed
        angular_velocity = turn_cmd * self.max_turn_rate * np.pi / 180.0  # rad/s
        
        # Integración
        self.heading += angular_velocity * self.sim_dt
        new_pos = self.pos + self.sim_dt * linear_velocity * np.array([
            np.cos(self.heading),
            np.sin(self.heading),
            0.0
        ])
        
        # Bounds checking (arena 100x100x10 mm)
        new_pos[0] = np.clip(new_pos[0], 0, 100)
        new_pos[1] = np.clip(new_pos[1], 0, 100)
        new_pos[2] = np.clip(new_pos[2], 0, 10)
        
        self.pos = new_pos
        
        # Logging
        step_idx = len(self.times)
        self.times.append(step_idx * self.sim_dt)
        self.positions.append(self.pos.copy())
        self.headings.append(self.heading)
        self.odor_concentrations.append(conc)
        self.brain_actions.append([forward_cmd, turn_cmd])
        
        # Generar y registrar ángulos articulares (modulados por comandos del cerebro)
        joint_angles = self._generate_joint_angles_for_step(step_idx, forward_cmd, turn_cmd)
        for joint_name, angle in joint_angles.items():
            self.angles_data[joint_name].append(angle)
        
        return True
    
    def run(self) -> bool:
        """
        Ejecutar simulación completa.
        
        Returns
        -------
        bool
            True si exitoso
        """
        print(f"\n[1/3] Ejecutando simulación ({self.n_steps} pasos)...")

        if HAS_TQDM:
            # Use tqdm progress bar if available
            with tqdm(total=self.n_steps, desc="  Simulando") as pbar:
                for step_idx in range(self.n_steps):
                    if not self.step():
                        print("  [X] Simulación interrumpida")
                        return False
                    pbar.update(1)
        else:
            # Fallback: print progress at intervals
            progress_interval = max(1, self.n_steps // 20)  # Print 20 updates
            for step_idx in range(self.n_steps):
                if not self.step():
                    print("  [X] Simulación interrumpida")
                    return False
                # Print progress updates
                if step_idx % progress_interval == 0 or step_idx == self.n_steps - 1:
                    percent = (step_idx + 1) / self.n_steps * 100
                    print(f"  Progreso: {percent:.1f}% ({step_idx + 1}/{self.n_steps} pasos)")

        print("  [OK] Simulación completada")
        return True
    
    def save_trajectory_data(self, output_dir: Path = None) -> Path:
        """
        Guardar datos de trayectoria y ángulos para visualización.
        
        Returns
        -------
        Path
            Ruta al archivo .pkl guardado
        """
        if output_dir is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M")
            output_dir = PROJECT_ROOT / "outputs" / "simulations" / "chemotaxis_3d" / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Preparar datos en formato que entienda MuJoCoRenderer
        data = {
            "times": np.array(self.times),
            "positions": np.array(self.positions),
            "headings": np.array(self.headings),
            "odor_concentrations": np.array(self.odor_concentrations),
            "brain_actions": np.array(self.brain_actions),
        }
        
        # Agregar ángulos en formato flat para compatibilidad
        for joint_name, angles_list in self.angles_data.items():
            data[joint_name] = np.array(angles_list)
        
        output_file = output_dir / "simulation_trajectory_3d.pkl"
        with open(output_file, "wb") as f:
            pickle.dump(data, f)
        
        print(f"  [OK] Datos de trayectoria guardados: {output_file}")
        return output_file


def render_3d_simulation(trajectory_file: Path, output_file: Path = None) -> bool:
    """
    Renderizar datos de simulación como video 3D usando MuJoCo.
    
    Parameters
    ----------
    trajectory_file : Path
        Archivo .pkl con datos de trayectoria
    output_file : Path, optional
        Nombre del archivo de salida
    
    Returns
    -------
    bool
        True si exitoso
    """
    if output_file is None:
        output_file = "NeuroMechFly_Chemotaxis_3D.mp4"
    
    if not HAS_MUJOCO_RENDERER:
        print("\n[2/3] [X] MuJoCoRenderer no disponible")
        print("  Instala FlyGym para renderización 3D:")
        print("  pip install flygym[vision]==0.2.7")
        return False
    
    print(f"\n[2/3] Configurando renderizador MuJoCo...")
    
    # Determinar directorio de salida basado en la ubicación del archivo .pkl
    # trajectory_file está en: outputs/simulations/chemotaxis_3d/{TIMESTAMP}/simulation_trajectory_3d.pkl
    output_dir = trajectory_file.parent  # outputs/simulations/chemotaxis_3d/{TIMESTAMP}/
    
    # Crear configuración
    config = RenderConfig(
        output_dir=output_dir,
        data_file=trajectory_file,
        fps=60,
        subsample=1,
        width=1920,
        height=1080
    )
    
    # Intentar renderizar
    try:
        renderer = MuJoCoRenderer(config)
        
        print(f"\n[3/3] Generando video 3D estabilizado...")
        success = renderer.render_and_save(output_file)
        
        if success:
            output_path = config.output_dir / output_file
            print(f"\n" + "="*70)
            print(f"[OK] VIDEO 3D GENERADO EXITOSAMENTE")
            print(f"  Archivo: {output_path}")
            print(f"  Resolución: {config.width}x{config.height}@{config.fps}fps")
            print("="*70)
            return True
        else:
            print("  [X] Error durante renderizado")
            return False
    
    except Exception as e:
        print(f"  [X] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Simulación 3D completa con navegación olfatoria"
    )
    parser.add_argument("--duration", type=float, default=15.0, help="Duración en segundos")
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    parser.add_argument("--skip-render", action="store_true", help="No renderizar video 3D")
    args = parser.parse_args()
    
    # Ejecutar simulación
    sim = CompleteOlfactorySimulation(
        odor_source=(50.0, 50.0, 5.0),
        odor_sigma=8.0,  # Sigma REDUCIDO para más pendiente del gradiente
        odor_amplitude=100.0,  # Amplitud suficiente
        start_pos=(35.0, 35.0, 3.0),  # Posición inicial MÁS CERCA (paso diagonal)
        sim_duration=args.duration,
        sim_dt=0.01,
        seed=args.seed
    )
    
    if not sim.run():
        print("[X] Simulación fallida")
        return False
    
    # Guardar datos
    trajectory_file = sim.save_trajectory_data()
    
    # Renderizar si no se especifica --skip-render
    if not args.skip_render:
        if not render_3d_simulation(trajectory_file):
            print("[X] Renderizado fallido")
            return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
