#!/usr/bin/env python3
"""
Environment Setup Module - Configura ambiente FlyGym para renderizado.

Responsabilidades:
- Inicializar FlyGym Fly model
- Configurar arena y física
- Configurar cámara (YawOnly y otras)
- Manejo de errores en inicialización

Separación de concernencias:
- Load Data ← data_loader.py
- Setup MuJoCo ← environment_setup.py (este módulo)
- Render Frames ← frame_renderer.py
- Save Video ← video_writer.py
"""

from typing import Optional, Tuple
from pathlib import Path
import numpy as np

try:
    from flygym import Fly, YawOnlyCamera, SingleFlySimulation
    from flygym.arena import FlatTerrain
    FLYGYM_AVAILABLE = True
except ImportError:
    FLYGYM_AVAILABLE = False


class EnvironmentSetup:
    """Configurador del ambiente FlyGym para renderizado."""
    
    def __init__(self, verbose: bool = True):
        """
        Inicializar setup.
        
        Args:
            verbose: Imprimir mensajes de estado
        """
        if not FLYGYM_AVAILABLE:
            raise ImportError("FlyGym no está instalado. Instala con: pip install flygym")
        
        self.verbose = verbose
        self.fly = None
        self.arena = None
        self.simulation = None
        self.camera = None
        
    def _log(self, msg: str):
        """Log con control de verbosity."""
        if self.verbose:
            print(msg)
    
    def setup_fly(self) -> bool:
        """
        Inicializar modelo de mosca Drosophila.
        
        Returns:
            True si setup exitoso
        """
        try:
            self._log("Inicializando modelo de mosca...")
            self.fly = Fly()
            self._log(f"  ✓ Fly creado")
            return True
        except Exception as e:
            self._log(f"ERROR creando Fly: {e}")
            return False
    
    def setup_arena(self, arena_type: str = "flat", **kwargs) -> bool:
        """
        Configurar arena de simulación.
        
        Args:
            arena_type: Tipo de arena ("flat", "terrain", etc.)
            **kwargs: Parámetros adicionales del arena
        
        Returns:
            True si setup exitoso
        """
        try:
            self._log(f"Configurando arena ({arena_type})...")
            
            if arena_type == "flat":
                self.arena = FlatTerrain()
            else:
                self._log(f"WARNING: Arena type '{arena_type}' no soportado, usando flat")
                self.arena = FlatTerrain()
            
            self._log(f"  ✓ Arena configurada")
            return True
        except Exception as e:
            self._log(f"ERROR configurando arena: {e}")
            return False
    
    def setup_simulation(self) -> bool:
        """
        Crear simulación SingleFlySimulation.
        
        Returns:
            True si setup exitoso
        """
        if self.fly is None or self.arena is None:
            self._log("ERROR: Fly o Arena no inicializados")
            return False
        
        try:
            self._log("Configurando simulación...")
            self.simulation = SingleFlySimulation(
                fly=self.fly,
                arena=self.arena,
            )
            self._log(f"  ✓ Simulación lista")
            return True
        except Exception as e:
            self._log(f"ERROR creando simulación: {e}")
            return False
    
    def setup_camera(
        self,
        camera_type: str = "yaw_only",
        **kwargs
    ) -> bool:
        """
        Configurar cámara de vista.
        
        Args:
            camera_type: Tipo de cámara ("yaw_only", "fixed", etc.)
            **kwargs: Parámetros de cámara
        
        Returns:
            True si setup exitoso
        """
        if self.simulation is None:
            self._log("ERROR: Simulación no inicializada")
            return False
        
        try:
            self._log(f"Configurando cámara ({camera_type})...")
            
            if camera_type == "yaw_only":
                # YawOnly = cámara sigue al fly rotando alrededor del eje Z
                self.camera = YawOnlyCamera(
                    sim=self.simulation,
                    **kwargs
                )
            else:
                self._log(f"WARNING: Camera type '{camera_type}' no soportado, usando yaw_only")
                self.camera = YawOnlyCamera(sim=self.simulation)
            
            self._log(f"  ✓ Cámara configurada")
            return True
        except Exception as e:
            self._log(f"ERROR configurando cámara: {e}")
            return False
    
    def setup_complete(self, **kwargs) -> bool:
        """
        Ejecutar setup completo en orden correcto.
        
        Args:
            **kwargs: Parámetros para cada componente
        
        Returns:
            True si todos los pasos fueron exitosos
        """
        self._log("Iniciando setup completo del ambiente...")
        
        steps = [
            ("Fly", self.setup_fly),
            ("Arena", lambda: self.setup_arena(arena_type=kwargs.get('arena_type', 'flat'))),
            ("Simulation", self.setup_simulation),
            ("Camera", lambda: self.setup_camera(camera_type=kwargs.get('camera_type', 'yaw_only'))),
        ]
        
        for name, setup_fn in steps:
            if not setup_fn():
                self._log(f"✗ Setup incompleto (falló en {name})")
                return False
        
        self._log("✓ Setup completo exitoso")
        return True
    
    def get_simulation(self):
        """Obtener instancia de simulación."""
        return self.simulation
    
    def get_camera(self):
        """Obtener instancia de cámara."""
        return self.camera
    
    def __repr__(self) -> str:
        """Representación string."""
        states = []
        if self.fly: states.append("fly✓")
        if self.arena: states.append("arena✓")
        if self.simulation: states.append("sim✓")
        if self.camera: states.append("cam✓")
        return f"EnvironmentSetup({','.join(states)})"
