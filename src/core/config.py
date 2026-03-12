"""
Configuración centralizada para el sistema de renderizado
Permite customizar todo aspecto del render sin tocar código
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any
from pathlib import Path


@dataclass
class CameraConfig:
    """Configuración de cámara 3D"""
    type: str = "fixed"
    distance: float = 12.0
    elevation: float = -15.0
    azimuth_start: float = 45.0
    azimuth_rotate: float = 0.5 
    lookat_body: str = "Thorax" # Mantener por compatibilidad
    follow_fly: bool = True     # Mantener por compatibilidad
    
    # Presets simplificados
    PRESETS = {
        "side_view": {"distance": 12.0, "elevation": -15, "azimuth_start": 90, "azimuth_rotate": 0},
        "top_view": {"distance": 15.0, "elevation": -60, "azimuth_start": 90, "azimuth_rotate": 0},
        "rotating": {"distance": 12.0, "elevation": -20, "azimuth_start": 45, "azimuth_rotate": 0.5},
        "iso_view": {"distance": 14.0, "elevation": 30, "azimuth_start": 45, "azimuth_rotate": 0.2},
        "close_up": {"distance": 8.0, "elevation": -10, "azimuth_start": 90, "azimuth_rotate": 0.3},
    }
    
    @classmethod
    def from_preset(cls, preset_name: str) -> "CameraConfig":
        if preset_name not in cls.PRESETS:
            return cls() # Default
        # Filtramos claves que no existan en la clase para evitar errores
        valid_keys = {k: v for k, v in cls.PRESETS[preset_name].items() if hasattr(cls, k)}
        return cls(**valid_keys)


@dataclass
class EnvironmentConfig:
    """Configuración del ambiente"""
    floor_enabled: bool = True
    floor_color: Tuple[float, float, float, float] = (0.8, 0.9, 1.0, 1.0)
    floor_size: Tuple[float, float, float] = (1000.0, 1000.0, 0.1) # Compatibilidad
    floor_pattern: str = "checkerboard"
    floor_reflection: float = 0.1
    
    # FlyGym terrain params
    terrain_config: Dict = field(default_factory=lambda: {"plane_size": (1000, 1000, 0.1)})


@dataclass
class PartHighlightConfig:
    """Configuración para destacar partes (RESTAURADO)"""
    leg: Optional[str] = None  # Resaltar una pata: "RF", "RM", etc.
    segment: Optional[str] = None  # "Coxa", "Femur", etc.
    highlight_opacity: float = 1.0
    shadow_opacity: float = 0.3
    highlight_color_override: Optional[Tuple[float, float, float]] = None


@dataclass
class LegColorConfig:
    """Configuración de colores para patas (RESTAURADO)"""
    colors: Dict[str, Tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "RF": (0.9, 0.3, 0.2, 1.0),
            "RM": (0.9, 0.6, 0.1, 1.0),
            "RH": (0.9, 0.8, 0.1, 1.0),
            "LF": (0.2, 0.6, 0.9, 1.0),
            "LM": (0.1, 0.7, 0.7, 1.0),
            "LH": (0.6, 0.4, 0.8, 1.0),
        }
    )
    
    def get_color(self, leg: str) -> Tuple[float, float, float, float]:
        return self.colors.get(leg, (0.5, 0.5, 0.5, 1.0))


@dataclass
class RenderConfig:
    """Configuración principal de renderizado"""
    
    # Archivos
    output_dir: Path = Path("./outputs/kinematic_replay")
    data_file: Path = Path("./data/inverse_kinematics/leg_joint_angles.pkl")
    
    # Video
    fps: int = 60
    subsample: int = 1
    width: int = 1920
    height: int = 1080
    codec: str = "libx264"
    quality: int = 9
    
    # Física (FlyGym Standard)
    physics_timestep: float = 1e-4
    run_physics: bool = True # Compatibilidad
    
    # Configuraciones modulares
    camera: CameraConfig = field(default_factory=CameraConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    
    # RESTAURADOS para compatibilidad con script principal
    highlight: PartHighlightConfig = field(default_factory=PartHighlightConfig)
    leg_colors: LegColorConfig = field(default_factory=LegColorConfig)
    
    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True, parents=True)


def create_moldeable_render(
    camera_preset: str = "rotating",
    fps: int = 60,
    subsample: int = 1,
    floor_enabled: bool = True,
    # Argumentos extra para compatibilidad (highlight, colors, etc.)
    highlight_leg: Optional[str] = None,
    highlight_segment: Optional[str] = None,
    custom_colors: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
    floor_size: Optional[Tuple[float, float, float]] = None,
    floor_color: Optional[Tuple[float, float, float, float]] = None,
    floor_pattern: Optional[str] = None,
    floor_reflection: Optional[float] = None,
    **kwargs 
) -> RenderConfig:
    """
    Factory para crear renders moldeables.
    """
    config = RenderConfig()
    
    # Configuración básica
    config.camera = CameraConfig.from_preset(camera_preset)
    config.fps = fps
    config.subsample = subsample
    
    # Configuración de ambiente
    config.environment.floor_enabled = floor_enabled
    if floor_color: config.environment.floor_color = floor_color
    if floor_size: config.environment.floor_size = floor_size
    
    # Configuración de Highlight (Restaurada)
    config.highlight.leg = highlight_leg
    config.highlight.segment = highlight_segment
    
    # Configuración de Colores (Restaurada)
    if custom_colors:
        config.leg_colors.colors.update(custom_colors)
    
    return config