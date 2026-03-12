"""
Módulo core - Funcionalidad central del sistema de renderizado
"""

from .config import (
    RenderConfig,
    CameraConfig,
    EnvironmentConfig,
    PartHighlightConfig,
    LegColorConfig,
)

from .data import (
    load_kinematic_data,
    format_joint_data,
    get_joint_names,
    get_leg_joints,
    get_n_frames
)

# Try to import model functions if available
try:
    from .model import (
        find_neuromechfly_model,
        load_and_setup_model,
        create_minimal_model,
        modify_xml_for_high_res
    )
except (ImportError, ModuleNotFoundError):
    # Model functions not available
    pass

__all__ = [
    # Config
    'RenderConfig',
    'CameraConfig',
    'EnvironmentConfig',
    'PartHighlightConfig',
    'LegColorConfig',
    
    # Data
    'load_kinematic_data',
    'format_joint_data',
    'get_joint_names',
    'get_leg_joints',
    'get_n_frames',
]