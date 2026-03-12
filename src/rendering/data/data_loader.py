#!/usr/bin/env python3
"""
Data Loader Module - Carga datos de simulación para renderizado.

Responsabilidades:
- Cargar datos crudos de simulación (.pkl)
- Validar integridad de datos
- Preparar datos en formato necesario para FlyGym
- Manejo de errores robusto

Separación de concernencias:
- Load Data ← data_loader.py (este módulo)
- Setup MuJoCo ← environment_setup.py
- Render Frames ← frame_renderer.py
- Save Video ← video_writer.py
"""

import pickle
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class DataLoader:
    """Cargador de datos cinemáticos para renderizado 3D."""
    
    def __init__(self, verbose: bool = True):
        """
        Inicializar data loader.
        
        Args:
            verbose: Imprimir mensajes de estado
        """
        self.verbose = verbose
        self.raw_data = None
        self.joint_angles = {}
        self.timestamps = []
        self.metadata = {}
        
    def _log(self, msg: str):
        """Log con control de verbosity."""
        if self.verbose:
            print(msg)
    
    def load_from_file(self, data_file: Path) -> bool:
        """
        Cargar datos de archivo .pkl.
        
        Args:
            data_file: Ruta al archivo .pkl
        
        Returns:
            True si carga exitosa
        """
        data_file = Path(data_file)
        if not data_file.exists():
            self._log(f"ERROR: Archivo no existe: {data_file}")
            return False
        
        try:
            self._log(f"Cargando datos de {data_file.name}...")
            with open(data_file, 'rb') as f:
                self.raw_data = pickle.load(f)
            
            self._log(f"  ✓ Datos cargados ({self._get_size_mb():.2f} MB)")
            return True
        except Exception as e:
            self._log(f"ERROR al cargar: {e}")
            return False
    
    def extract_joint_angles(self) -> bool:
        """
        Extraer ángulos articulares del raw data.
        
        Expected data format:
        {
            'joint_angles': {joint_name: [angle_t0, angle_t1, ...]},
            'timestamps': [t0, t1, ...],
            ...
        }
        
        Returns:
            True si extracción exitosa
        """
        if self.raw_data is None:
            self._log("ERROR: No hay datos cargados. Llama load_from_file() primero.")
            return False
        
        try:
            self._log("Extrayendo ángulos articulares...")
            
            # Verificar estructura esperada
            if 'joint_angles' not in self.raw_data:
                self._log("WARNING: 'joint_angles' no encuentra en raw_data")
                return False
            
            self.joint_angles = self.raw_data['joint_angles']
            self.timestamps = self.raw_data.get('timestamps', [])
            self.metadata = self.raw_data.get('metadata', {})
            
            # Validar consistencia
            if not self.joint_angles:
                self._log("ERROR: joint_angles vacío")
                return False
            
            # Obtener número de frames
            first_joint = list(self.joint_angles.keys())[0]
            n_frames = len(self.joint_angles[first_joint])
            
            self._log(f"  ✓ {len(self.joint_angles)} joints extraídos")
            self._log(f"  ✓ {n_frames} frames de animación")
            
            return True
        except Exception as e:
            self._log(f"ERROR extrayendo joints: {e}")
            return False
    
    def validate_data_integrity(self) -> Tuple[bool, str]:
        """
        Validar integridad de datos cargados.
        
        Returns:
            (is_valid, message)
        """
        if not self.joint_angles:
            return False, "No hay datos de joints"
        
        # Verificar que todos los joints tienen mismo número de frames
        joint_names = list(self.joint_angles.keys())
        frame_counts = [len(angles) for angles in self.joint_angles.values()]
        
        if len(set(frame_counts)) > 1:
            return False, f"Inconsistencia: joints con diferentes frame counts: {set(frame_counts)}"
        
        if frame_counts[0] == 0:
            return False, "Ningún frame disponible"
        
        # Verificar que los valores son numéricos
        try:
            for joint_name, angles in self.joint_angles.items():
                angles_array = np.asarray(angles)
                if not np.isfinite(angles_array).all():
                    return False, f"Joint {joint_name} contiene NaN o Inf"
        except Exception as e:
            return False, f"Error validando valores: {e}"
        
        return True, f"✓ Datos válidos: {len(joint_names)} joints, {frame_counts[0]} frames"
    
    def get_joint_angles(self) -> Dict[str, np.ndarray]:
        """
        Obtener ángulos articulares como numpy arrays.
        
        Returns:
            Dict[joint_name, angle_array]
        """
        return {
            name: np.asarray(angles)
            for name, angles in self.joint_angles.items()
        }
    
    def get_n_frames(self) -> int:
        """Obtener número total de frames."""
        if not self.joint_angles:
            return 0
        first_joint = list(self.joint_angles.keys())[0]
        return len(self.joint_angles[first_joint])
    
    def _get_size_mb(self) -> float:
        """Calcular tamaño de datos en MB."""
        if self.raw_data is None:
            return 0
        return len(pickle.dumps(self.raw_data)) / (1024 * 1024)
    
    def __repr__(self) -> str:
        """Representación string."""
        n_frames = self.get_n_frames()
        n_joints = len(self.joint_angles)
        size = self._get_size_mb()
        return f"DataLoader(frames={n_frames}, joints={n_joints}, size={size:.2f}MB)"
