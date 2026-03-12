"""
Rendering module for NeuroMechFly 3D visualization.
Handles MuJoCo rendering and 3D visualization with modular architecture.

Modular components:
- DataLoader: Carga datos cinemáticos (.pkl)
- EnvironmentSetup: Configura FlyGym y simulación
- FrameRenderer: Renderiza frames desde datos
- VideoWriter: Guarda frames como video MP4
- RenderingPipeline: Orquestador del flujo completo (RECOMENDADO)
"""

try:
    # Imports desde submódulos organizados
    from .data.data_loader import DataLoader
    from .data.environment_setup import EnvironmentSetup
    from .core.frame_renderer import FrameRenderer
    from .core.video_writer import VideoWriter
    from .pipeline.rendering_pipeline import RenderingPipeline
    from .core.mujoco_renderer import MuJoCoRenderer  # Legacy
    
    __all__ = [
        'DataLoader',
        'EnvironmentSetup',
        'FrameRenderer',
        'VideoWriter',
        'RenderingPipeline',
        'MuJoCoRenderer',  # Legacy, mantener para compatibilidad
    ]
except ImportError as e:
    print(f"Warning: No se pudieron importar módulos de rendering: {e}")
    # Fallback a MuJoCoRenderer antiguo
    try:
        from .core.mujoco_renderer import MuJoCoRenderer
        __all__ = ['MuJoCoRenderer']
    except:
        __all__ = []

