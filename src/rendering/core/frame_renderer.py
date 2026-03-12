#!/usr/bin/env python3
"""
Frame Renderer Module - Renderiza frames de simulación a imágenes.

Responsabilidades:
- Ejecutar simulation steps con datos cinemáticos
- Capturar frames del renderizado
- Manejo de errores durante renderizado
- Progress tracking

Separación de concernencias:
- Load Data ← data_loader.py
- Setup MuJoCo ← environment_setup.py
- Render Frames ← frame_renderer.py (este módulo)
- Save Video ← video_writer.py
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm


class FrameRenderer:
    """Renderizador de frames para animación 3D."""
    
    def __init__(
        self,
        simulation,
        joint_angles: Dict[str, np.ndarray],
        verbose: bool = True
    ):
        """
        Inicializar frame renderer.
        
        Args:
            simulation: SingleFlySimulation instance
            joint_angles: Dict[joint_name, angle_array]
            verbose: Imprimir progreso
        """
        self.simulation = simulation
        self.joint_angles = joint_angles
        self.verbose = verbose
        self.frames = []
        self.render_errors = []
        self.timestamps = []
        
    def _log(self, msg: str):
        """Log con control de verbosity."""
        if self.verbose:
            print(msg)
    
    def render_frames(self, fps: int = 60) -> bool:
        """
        Renderizar todos los frames desde datos cinemáticos.
        
        Args:
            fps: Frames per second para estimación de duración
        
        Returns:
            True si renderizado exitoso
        """
        if not self.joint_angles:
            self._log("ERROR: No hay datos de joints")
            return False
        
        # Obtener número de frames
        joint_names = list(self.joint_angles.keys())
        n_frames = len(self.joint_angles[joint_names[0]])
        
        if n_frames == 0:
            self._log("ERROR: No hay frames en los datos")
            return False
        
        self._log(f"Renderizando {n_frames} frames (durará ~{n_frames/fps:.1f}s)...")
        self.frames = []
        self.render_errors = []
        
        try:
            with tqdm(total=n_frames, desc="Renderizando", disable=not self.verbose) as pbar:
                for frame_idx in range(n_frames):
                    try:
                        # Compilar acción para este frame
                        action = {}
                        for joint_name in joint_names:
                            action[joint_name] = self.joint_angles[joint_name][frame_idx]
                        
                        # Ejecutar step de simulación
                        obs, info = self.simulation.step(action)
                        
                        # Renderizar frame
                        frame = self._render_frame(frame_idx)
                        if frame is not None:
                            self.frames.append(frame)
                            self.timestamps.append(frame_idx / fps)
                        else:
                            self._log(f"  WARNING: Frame {frame_idx} no se pudo renderizar")
                            self.render_errors.append(frame_idx)
                    
                    except Exception as e:
                        self._log(f"  ERROR en frame {frame_idx}: {e}")
                        self.render_errors.append(frame_idx)
                    
                    pbar.update(1)
            
            success_count = len(self.frames)
            error_count = len(self.render_errors)
            
            self._log(f"✓ Renderizado completado")
            self._log(f"  {success_count}/{n_frames} frames renderizados correctamente")
            
            if error_count > 0:
                self._log(f"  ⚠ {error_count} frames con error (indices: {self.render_errors[:10]}...)")
            
            return len(self.frames) > 0
        
        except Exception as e:
            self._log(f"ERROR durante renderizado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _render_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        """
        Renderizar un frame individual.
        
        Args:
            frame_idx: Índice del frame
        
        Returns:
            Frame como numpy array o None si falla
        """
        try:
            # Intentar obtener frame del simulador
            # Nota: El método exacto depende de la versión de FlyGym
            
            # Opción 1: render() devuelve frame directamente
            if hasattr(self.simulation, 'render'):
                return self.simulation.render()
            
            # Opción 2: Se necesita usar camera para obtener frame
            elif hasattr(self.simulation, 'camera'):
                frame = self.simulation.camera.render()
                return frame
            
            # Opción 3: Buscar atributo de renderizado
            elif hasattr(self.simulation, '_render'):
                return self.simulation._render()
            
            # Si ninguna opción funciona, crear frame dummy
            else:
                self._log(f"  WARNING: No se pudo determinar método de renderizado")
                return np.zeros((480, 640, 3), dtype=np.uint8)
        
        except Exception as e:
            self._log(f"    Error renderizando frame {frame_idx}: {e}")
            return None
    
    def get_frames(self) -> List[np.ndarray]:
        """Obtener lista de frames renderizados."""
        return self.frames
    
    def get_frame_count(self) -> int:
        """Obtener número de frames renderizados."""
        return len(self.frames)
    
    def get_error_count(self) -> int:
        """Obtener número de frames con error."""
        return len(self.render_errors)
    
    def get_error_indices(self) -> List[int]:
        """Obtener índices de frames que fallaron."""
        return self.render_errors
    
    def __repr__(self) -> str:
        """Representación string."""
        return f"FrameRenderer(frames={len(self.frames)}, errors={len(self.render_errors)})"
