"""
Módulo Core de Rendering - Componentes Principales

Contiene los módulos centrales para renderizar frames individuales,
codificar video y gestionar la interfaz con MuJoCo.

Clases:
    - FrameRenderer: Renderiza frames individuales desde MuJoCo
    - VideoWriter: Codifica frames a video MP4
    - MuJoCoRenderer: Orquestador principal de rendering (legado)
"""

from .frame_renderer import FrameRenderer
from .video_writer import VideoWriter
from .mujoco_renderer import MuJoCoRenderer

__all__ = ["FrameRenderer", "VideoWriter", "MuJoCoRenderer"]
