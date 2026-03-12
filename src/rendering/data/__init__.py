"""
Módulo de Carga de Datos - Rendering

Contiene componentes para cargar y preparar datos de simulación
para su renderizado en video 3D.

Clases:
    - DataLoader: Carga datos de archivos .pkl
    - EnvironmentSetup: Configura el ambiente MuJoCo para rendering
"""

from .data_loader import DataLoader
from .environment_setup import EnvironmentSetup

__all__ = ["DataLoader", "EnvironmentSetup"]
