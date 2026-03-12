#!/usr/bin/env python3
"""
Video Writer Module - Guarda frames renderizados como video MP4.

Responsabilidades:
- Guardar frames como video MP4
- Validar frames antes de guardar
- Manejo de códecs y calidad
- Información de resultado

Separación de concernencias:
- Load Data ← data_loader.py
- Setup MuJoCo ← environment_setup.py
- Render Frames ← frame_renderer.py
- Save Video ← video_writer.py (este módulo)
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
import imageio


class VideoWriter:
    """Escritor de video MP4 a partir de frames."""
    
    SUPPORTED_FORMATS = ['mp4', 'avi', 'mov', 'gif']
    DEFAULT_CODEC = 'libx264'  # Para MP4
    DEFAULT_QUALITY = 5  # 1-31, menor = mejor calidad (para H.264)
    
    def __init__(self, verbose: bool = True):
        """
        Inicializar video writer.
        
        Args:
            verbose: Imprimir mensajes de estado
        """
        self.verbose = verbose
        self.last_output_path = None
        self.last_frame_count = 0
        self.last_duration = None
        
    def _log(self, msg: str):
        """Log con control de verbosity."""
        if self.verbose:
            print(msg)
    
    def validate_frames(self, frames: List[np.ndarray]) -> Tuple[bool, str]:
        """
        Validar que los frames sean válidos para video.
        
        Args:
            frames: Lista de frames (numpy arrays)
        
        Returns:
            (is_valid, message)
        """
        if not frames:
            return False, "Lista de frames vacía"
        
        if len(frames) < 2:
            return False, "Se necesitan al menos 2 frames"
        
        # Obtener dimensiones esperadas del primer frame
        first_shape = frames[0].shape
        
        # Validar todos los frames
        for i, frame in enumerate(frames):
            if not isinstance(frame, np.ndarray):
                return False, f"Frame {i} no es numpy array: {type(frame)}"
            
            if frame.shape != first_shape:
                return False, f"Frame {i} tiene forma diferente: {frame.shape} vs {first_shape}"
            
            if not np.isfinite(frame).all():
                return False, f"Frame {i} contiene NaN o Inf"
        
        return True, f"✓ {len(frames)} frames válidos ({first_shape})"
    
    def save_video(
        self,
        frames: List[np.ndarray],
        output_path: Path,
        fps: int = 60,
        quality: int = 5,
        codec: Optional[str] = None,
    ) -> bool:
        """
        Guardar frames como video MP4.
        
        Args:
            frames: Lista de frames (numpy arrays)
            output_path: Ruta de salida (.mp4, .avi, etc.)
            fps: Frames per second
            quality: Calidad de compresión (1-31, menor=mejor)
            codec: Codec (default='libx264' para MP4)
        
        Returns:
            True si guardado exitoso
        """
        output_path = Path(output_path)
        
        # Validar frames
        valid, msg = self.validate_frames(frames)
        if not valid:
            self._log(f"ERROR: {msg}")
            return False
        
        self._log(f"Validación de frames: {msg}")
        
        # Validar formato
        suffix = output_path.suffix.lower().lstrip('.')
        if suffix not in self.SUPPORTED_FORMATS:
            self._log(f"WARNING: Formato '{suffix}' puede no ser soportado")
        
        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self._log(f"Guardando video: {output_path.name}")
            self._log(f"  Frames: {len(frames)}")
            self._log(f"  FPS: {fps}")
            self._log(f"  Resolución: {frames[0].shape[1]}x{frames[0].shape[0]}")
            self._log(f"  Duración: {len(frames)/fps:.2f}s")
            
            # Guardar video
            if suffix == 'mp4' or suffix == 'avi':
                # Para MP4 y AVI usar imageio con codec
                codec_arg = codec or self.DEFAULT_CODEC
                pixelformat = 'yuv420p' if suffix == 'mp4' else None
                
                writer = imageio.get_writer(
                    output_path,
                    fps=fps,
                    codec=codec_arg,
                    pixelformat=pixelformat,
                )
                
                for frame in frames:
                    # Asegurar que el frame es uint8
                    if frame.dtype != np.uint8:
                        frame = np.clip(frame * 255, 0, 255).astype(np.uint8)
                    writer.append_data(frame)
                
                writer.close()
            else:
                # Para GIF y otros formatos
                # Convertir a uint8 si es necesario
                frames_uint8 = []
                for frame in frames:
                    if frame.dtype != np.uint8:
                        frame_uint8 = np.clip(frame * 255, 0, 255).astype(np.uint8)
                    else:
                        frame_uint8 = frame
                    frames_uint8.append(frame_uint8)
                
                imageio.mimsave(output_path, frames_uint8, fps=fps)
            
            self._log(f"✓ Video guardado: {output_path}")
            
            # Registrar info
            self.last_output_path = output_path
            self.last_frame_count = len(frames)
            self.last_duration = len(frames) / fps
            
            return True
        
        except Exception as e:
            self._log(f"ERROR guardando video: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_last_output_info(self) -> dict:
        """Obtener información del último video guardado."""
        if self.last_output_path is None:
            return {}
        
        return {
            'path': str(self.last_output_path),
            'frames': self.last_frame_count,
            'duration_seconds': self.last_duration,
            'size_mb': self.last_output_path.stat().st_size / (1024*1024) if self.last_output_path.exists() else None,
        }
    
    def __repr__(self) -> str:
        """Representación string."""
        if self.last_output_path:
            return f"VideoWriter(last={self.last_output_path.name}, frames={self.last_frame_count})"
        return "VideoWriter(sin video guardado)"
