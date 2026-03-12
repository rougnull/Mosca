#!/usr/bin/env python3
"""
Renderizador FlyGym - VISTA ESTABILIZADA (YawOnly)

Características:
- Interfaz dual: soporta RenderConfig o sim_dir
- Cámara estabilizada con YawOnly seguimiento
- Renderizado 3D con FlyGym/MuJoCo

Uso:
    # Con RenderConfig (desde run_complete_3d_simulation)
    renderer = MuJoCoRenderer(config)
    renderer.render_and_save(output_file)
    
    # Con sim_dir (desde línea de comandos)
    renderer = MuJoCoRenderer(simulation_directory)
    renderer.render_to_mp4()
"""

import numpy as np
from pathlib import Path
from tqdm import tqdm
import imageio
from typing import Optional, Dict, Any, Union

from flygym import Fly, YawOnlyCamera, SingleFlySimulation
from flygym.arena import FlatTerrain
from flygym.preprogrammed import all_leg_dofs

# Importar wrapper de rendering continuo
try:
    from .continuous_simulation import ContinuousRenderingSimulation
    HAS_CONTINUOUS_RENDERING = True
except ImportError:
    HAS_CONTINUOUS_RENDERING = False
    ContinuousRenderingSimulation = None

try:
    from src.core.config import RenderConfig
    from src.core.data import load_kinematic_data, format_joint_data, get_n_frames
except ImportError:
    try:
        # Fallback: importar desde rutas relativas
        from ...core.config import RenderConfig
        from ...core.data import load_kinematic_data, format_joint_data, get_n_frames
    except ImportError:
        # Fallback final: mismo nivel o sys.path
        try:
            from pathlib import Path
            import sys
            src_path = Path(__file__).parent.parent.parent  # src/
            sys.path.insert(0, str(src_path))
            from core.config import RenderConfig
            from core.data import load_kinematic_data, format_joint_data, get_n_frames
        except ImportError:
            RenderConfig = None
            load_kinematic_data = None
            format_joint_data = None
            get_n_frames = None


class MuJoCoRenderer:
    """Renderizador FlyGym con vista estabilizada YawOnly."""
    
    def __init__(self, config_or_path: Union[Any, str]):
        """
        Inicializar renderer - soporta RenderConfig o sim_dir.
        
        Args:
            config_or_path: RenderConfig o ruta a directorio de simulación
        """
        if isinstance(config_or_path, str):
            # Interfaz sim_dir
            self.sim_dir = Path(config_or_path)
            self.config = None
        elif config_or_path.__class__.__name__ == 'RenderConfig':
            # Interfaz RenderConfig
            self.config = config_or_path
            self.sim_dir = self.config.output_dir if hasattr(self.config, 'output_dir') else None
        else:
            raise TypeError(f"Esperaba RenderConfig o str, recibí {type(config_or_path)}")
        
        self.sim = None
        self.fly = None
        self.cam = None
        self.formatted_data = None
        self.frames = []
        
    def load_data(self) -> bool:
        """Cargar datos cinemáticos."""
        try:
            print("[1/4] Cargando datos cinemáticos...")
            if self.config:
                raw_data = load_kinematic_data(self.config.data_file)
                self.formatted_data = format_joint_data(raw_data, self.config.subsample)
                print(f"  [OK] {len(self.formatted_data)} frames cargados")
                return True
            else:
                print("  [X] No hay config disponible")
                return False
        except Exception as e:
            print(f"  [X] Error: {e}")
            return False

    def _setup_environment(self):
        """Configurar ambiente FlyGym con postura inicial válida."""
        print(f"[2/4] Configurando simulación...")
        
        # CRÍTICO: Crear Fly con postura estabilizada y control de posición
        self.fly = Fly(
            init_pose="stretch",  # Postura inicial válida del robot
            actuated_joints=all_leg_dofs,  # 42 DoF (6 legs × 7 joints)
            control="position",  # Control de posición (ángulos absolutos)
        )
        
        # Crear arena
        arena = FlatTerrain()
        
        # CRÍTICO: Usar ContinuousRenderingSimulation si está disponible
        # FlyGym 0.2.7 no renderiza en cada step por defecto
        # Este wrapper asegura que render() devuelva frame en CADA step
        if HAS_CONTINUOUS_RENDERING and ContinuousRenderingSimulation:
            print(f"  [*] Usando ContinuousRenderingSimulation (rendering cada step)")
            self.sim = ContinuousRenderingSimulation(fly=self.fly, arena=arena)
        else:
            print(f"  [!] ContinuousRenderingSimulation no disponible, usando SingleFlySimulation")
            self.sim = SingleFlySimulation(fly=self.fly, arena=arena)
        
        # Resetear simulación para obtener estado inicial válido
        self.obs, self.info = self.sim.reset()
        print(f"  [OK] Simulación configurada correctamente.")

    def render(self) -> bool:
        """Renderizar simulación."""
        if not self.formatted_data:
            print("  [X] No hay datos formateados")
            return False
        
        print(f"[3/4] Generando video estabilizado...")
        
        try:
            # formatted_data es un Dict[joint_name, angle_array]
            # Necesitamos compilar un array de 42 elementos (6 legs * 7 DOF)
            joint_names = sorted(list(self.formatted_data.keys()))
            n_frames = len(self.formatted_data[joint_names[0]]) if joint_names else 0
            
            if n_frames == 0:
                print("  [X] No hay frames en los datos")
                return False
            
            n_joints = len(joint_names)
            print(f"  [Info] Usando {n_joints} joints detectados")
            
            # Parámetro CRÍTICO: Frames iniciales para estabilizar simulación física
            # Los primeros frames pueden tener inestabilidad numérica
            # Los saltamos y dejamos que MuJoCo se estabilice
            skip_initial_frames = 10  # Saltar primeros 10 frames para estabilización
            
            # Suavizar transición: interpolar entre stretch (0) y primer frame del pickle
            transition_frames = min(5, max(1, n_frames // 20))  # 5% de transición, min 1 frame
            
            last_valid_frame = None  # Guardar último frame válido para casos donde render() falla
            frames_skipped = 0
            frames_with_errors = 0
            
            with tqdm(total=n_frames, desc="  Renderizando") as pbar:
                for frame_idx in range(n_frames):
                    try:
                        # Compilar array de acciones para este frame desde todos los joints
                        # FlyGym espera: {"joints": numpy_array}
                        action_values = []
                        
                        # CRÍTICO: Smooth transition en los primeros frames
                        if frame_idx < transition_frames:
                            # Interpolar suavemente: blend inicial angles -> target angles
                            blend_factor = frame_idx / max(1, transition_frames - 1)
                            for joint_name in joint_names:
                                val = self.formatted_data[joint_name][0]  # Usar primer frame como referencia
                                if isinstance(val, (list, np.ndarray)):
                                    val = float(val[0]) if len(val) > 0 else 0.0
                                else:
                                    val = float(val)
                                # Suavizar: favor hacia los valores del pickle
                                smoothed_val = val * blend_factor
                                action_values.append(smoothed_val)
                        else:
                            # Después de transición, usar ángulos normales
                            for joint_name in joint_names:
                                val = self.formatted_data[joint_name][frame_idx]
                                # Asegurar que es un escalar
                                if isinstance(val, (list, np.ndarray)):
                                    val = float(val[0]) if len(val) > 0 else 0.0
                                else:
                                    val = float(val)
                                action_values.append(val)
                        
                        action_array = np.array(action_values, dtype=np.float32)
                        
                        # Crear estructura de acción esperada por FlyGym
                        action = {"joints": action_array}
                        
                        # Ejecutar step de simulación
                        obs = self.sim.step(action)
                        
                        # CRITICAL: Saltar primeros frames para estabilización
                        # La simulación física necesita tiempo para estabilizarse
                        # Los primeros frames tienen errores numéricos MUJOCO
                        if frame_idx < skip_initial_frames:
                            frames_skipped += 1
                            pbar.update(1)
                            continue
                        
                        # Renderizar - devuelve una lista [frame_array] o [None]
                        frame_list = self.sim.render()
                        
                        if frame_list is not None and len(frame_list) > 0:
                            frame = frame_list[0]
                            
                            # IMPORTANTE: frame puede ser None incluso si frame_list tiene elementos
                            if frame is not None:
                                self.frames.append(frame)
                                last_valid_frame = frame
                            elif last_valid_frame is not None:
                                # Render devolvió None - reutilizar último frame válido
                                # Esto previene "huecos" en el video cuando MuJoCo tiene problemas
                                self.frames.append(last_valid_frame)
                                frames_with_errors += 1
                            
                    except Exception as e:
                        # Capturar excepciones pero continuar
                        if frame_idx >= skip_initial_frames:
                            frames_with_errors += 1
                            if last_valid_frame is not None:
                                # Usar último frame válido como fallback
                                self.frames.append(last_valid_frame)
                        # No lanzar excepción - continuar con siguiente frame
                    
                    pbar.update(1)
            
            print(f"  [OK] {len(self.frames)} frames renderizados (salteados {frames_skipped} iniciales)", end="")
            if frames_with_errors > 0:
                print(f", {frames_with_errors} con fallback")
            else:
                print()
            
            if len(self.frames) < n_frames // 4:
                print(f"  [!] ADVERTENCIA: Solo {len(self.frames)} de {n_frames - frames_skipped} frames")
            
            return len(self.frames) > 0
        except Exception as e:
            print(f"  [X] Error renderizando: {e}")
            import traceback
            traceback.print_exc()
            return False

    def render_and_save(self, output_file: str) -> bool:
        """
        Pipeline completo: cargar, renderizar y guardar.
        
        Args:
            output_file: Nombre del archivo MP4 destino
        
        Returns:
            True si éxito
        """
        # Load
        if not self.load_data():
            return False
        
        # Setup
        try:
            self._setup_environment()
        except Exception as e:
            print(f"  [X] Error configurando ambiente: {e}")
            return False
        
        # Render
        if not self.render():
            return False
        
        # Save
        print(f"[4/4] Guardando video...")
        try:
            output_path = self.config.output_dir / output_file if self.config else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Validar y preparar frames para guardar
            validated_frames = []
            for frame in self.frames:
                if isinstance(frame, np.ndarray):
                    # Asegurar que es uint8 y tiene 3 canales
                    if frame.dtype != np.uint8:
                        frame = np.uint8(np.clip(frame * 255, 0, 255))
                    if len(frame.shape) == 2:  # Grayscale
                        frame = np.stack([frame] * 3, axis=-1)  # Convertir a RGB
                    validated_frames.append(frame)
            
            if not validated_frames:
                print(f"  [X] No hay frames válidos para guardar")
                return False
            
            # Guardar frames como video MP4
            fps_value = self.config.fps if self.config else 60
            imageio.mimsave(str(output_path), validated_frames, fps=fps_value)
            
            print(f"  [OK] Video guardado: {output_path}")
            return True
        except Exception as e:
            print(f"  [X] Error guardando: {e}")
            import traceback
            traceback.print_exc()
            return False

    def render_to_mp4(self, output_path: Optional[str] = None, fps: int = 60) -> bool:
        """Interfaz simplificada para render_and_save."""
        if output_path is None:
            output_path = "fly_3d_animation.mp4"
        return self.render_and_save(output_path)
