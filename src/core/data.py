"""
Carga y procesamiento de datos cinemáticos
Centraliza la lógica de formateo de datos para evitar duplicación
"""

import pickle
from pathlib import Path
from typing import Dict, List
import numpy as np


def load_kinematic_data(data_file: Path) -> Dict:
    """
    Carga datos de cinemática desde archivo pickle
    
    Args:
        data_file: Ruta al archivo pickle con datos
        
    Returns:
        Dict con datos crudos
    """
    if not data_file.exists():
        raise FileNotFoundError(f"Archivo de datos no encontrado: {data_file}")
    
    with open(data_file, "rb") as f:
        return pickle.load(f)


def format_joint_data(raw_data: Dict, subsample: int = 1) -> Dict[str, np.ndarray]:
    """
    Convierte formato de datos FlyGym (seqikpy) a formato MuJoCo interno
    
    Mapeo de segmentos:
        ThC   -> Coxa
        CTr   -> Femur
        FTi   -> Tibia
        TiTa  -> Tarsus1
    
    Args:
        raw_data: Datos crudos del archivo pickle
        subsample: Tomar cada N frames
        
    Returns:
        Dict con formato: {"joint_LEGSegment": array_ángulos, ...}
    """
    formatted = {}
    
    # Mapeo de nombres de segmentos
    segment_mapping = {
        "ThC": "Coxa",
        "CTr": "Femur",
        "FTi": "Tibia",
        "TiTa": "Tarsus1"
    }
    
    # Detectar si los datos están en grados o radianes
    # Si encontramos valores > 7.0 (2*pi es ~6.28), asumimos grados
    max_val_detected = 0.0
    
    for joint, values in raw_data.items():
        if joint in ["meta", "swing_stance_time"] or not isinstance(values, (list, np.ndarray)):
            continue
        current_max = np.max(np.abs(values))
        if current_max > max_val_detected:
            max_val_detected = current_max
            
    # Umbral de seguridad: 2 * PI + margen
    is_degrees = max_val_detected > 6.5
    if is_degrees:
        print(f"  [Data] Detectados valores > 2π (Max: {max_val_detected:.2f}). Convirtiendo GRADOS -> RADIANES.")

    for joint, values in raw_data.items():
        # Ignorar metadatos
        if joint in ["meta", "swing_stance_time"]:
            continue
        
        # Parsear nombre de joint
        # Formato esperado: "walkerJoin_XX_LEG_SEGMENT_DOF"
        try:
            leg = joint[6:8]  # Posiciones 6-7 son el leg code
            joint_name = joint[9:]  # Después del guión bajo
            
            if "_" in joint_name:
                parts = joint_name.split("_")
                segment = parts[0]
                dof = parts[1] if len(parts) > 1 else "pitch"
            else:
                segment = joint_name
                dof = "pitch"
            
            segment_name = segment_mapping.get(segment, segment)
            
            if dof == "pitch":
                new_key = f"joint_{leg}{segment_name}"
            else:
                new_key = f"joint_{leg}{segment_name}_{dof}"
            
            if isinstance(values, (list, np.ndarray)):
                vals = np.array(values)[::subsample]
                
                # CONVERSIÓN CRÍTICA PARA EVITAR EXPLOSIONES
                if is_degrees:
                    vals = np.deg2rad(vals)
                    
                formatted[new_key] = vals
            
        except (IndexError, ValueError, KeyError) as e:
            continue
    
    if not formatted:
        raise ValueError("No se pudieron extraer datos de joints del archivo. Verifica el formato de datos.")
    
    return formatted


def get_joint_names(formatted_data: Dict) -> List[str]:
    """Obtener nombres de joints formateados"""
    return list(formatted_data.keys())


def get_leg_joints(formatted_data: Dict, leg: str) -> Dict[str, np.ndarray]:
    """Obtener todos los joints de una pata específica"""
    prefix = f"joint_{leg}"
    return {k: v for k, v in formatted_data.items() if k.startswith(prefix)}


def get_n_frames(formatted_data: Dict) -> int:
    """Obtener número total de frames de animación"""
    if not formatted_data:
        return 0
    first_key = list(formatted_data.keys())[0]
    return len(formatted_data[first_key])