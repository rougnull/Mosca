#!/usr/bin/env python3
"""
BRAIN ISOLATION TEST - COMPREHENSIVE CHEMOTAXIS ANALYSIS (REFACTORED + ENHANCED)

Simulation exhaustiva del cerebro olfatorio de Drosophila con:
1. Variables configurables (NUM_STEPS, DT, velocidades, escalas)
2. Ejecución eficiente con logging mínimo en consola
3. Captura EXHAUSTIVA de datos técnicos por paso
4. Análisis avanzado: velocidades, aceleraciones, convergencia, oscilaciones
5. Múltiples formatos de salida: JSON, CSV, NPZ, PNG
6. Reporte técnico completo (sin imprimir en consola)
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
import json
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal  # Para análisis de oscilaciones

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controllers.brain.modular_brain import ModularBrain
from olfaction.odor_field import OdorField


# ===========================
# CONFIGURACIÓN (EDITAR AQUÍ)
# ===========================
NUM_STEPS = 20000              # Número de pasos de simulación
DT = 0.01                      # Segundos por paso
MAX_SPEED = 4.0                # mm/s (velocidad máxima)
MAX_TURN_RATE = 1.8            # rad/s (giro máximo)
VERBOSE = True                 # Logs en consola
LOG_EVERY = 50                 # Cada cuántos pasos imprimir logs
OUTPUT_BASE = Path("outputs") / "tests" / "brain"
ODOR_SOURCE = np.array([50.0, 50.0, 5.0])  # Fuente de olor (x, y, z)
ODOR_Z_SAMPLE = 1.8            # Altura z para sensado

# ===========================
# TEST HARDCODED: ENABLE/DISABLE OBSTÁCULOS AQUÍ  
# ===========================
ENABLE_OBSTACLES = True       # <<< CAMBIAR A True PARA PRUEBAS CON PAREDES

# Configuración de obstáculos (ignorada si ENABLE_OBSTACLES=False)
OBSTACLE_WALLS = [(40.0, 40.0, 40.0, 60.0)]  # Pared vertical
OBSTACLE_RADIUS = 0.3
OBSTACLE_SENSING_DISTANCE = 3.0

# Posiciones iniciales
INITIAL_POS_NORMAL = np.array([35.0, 35.0, 1.8])
INITIAL_HEADING_NORMAL = np.radians(30.0)

INITIAL_POS_OBSTACLES = np.array([30.0, 55.0, 1.8])
INITIAL_HEADING_OBSTACLES = np.radians(180.0)


# ===========================
# SETUP Y UTILITIES
# ===========================

def create_output_dir() -> Tuple[Path, str]:
    """Crear carpeta de salida con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    outdir = (PROJECT_ROOT / OUTPUT_BASE / timestamp).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir, timestamp


def distance_point_to_line(
    point: np.ndarray,
    line_start: np.ndarray,
    line_end: np.ndarray
) -> float:
    """
    Calcular distancia perpendicular de un punto a una línea infinita.
    Params:
      point: (x, y)
      line_start: (x, y)
      line_end: (x, y)
    Returns:
      distancia (float)
    """
    # Vector de línea
    line_vec = line_end - line_start
    line_len = np.linalg.norm(line_vec)
    if line_len < 1e-6:
        return float(np.linalg.norm(point - line_start))
    
    # Vector desde line_start a point
    point_vec = point - line_start
    
    # Proyectar point sobre line
    line_unit = line_vec / line_len
    proj_length = np.dot(point_vec, line_unit)
    
    # Punto proyectado
    proj_point = line_start + proj_length * line_unit
    
    # Distancia
    dist = np.linalg.norm(point - proj_point)
    return float(dist)


def check_collision_with_walls(
    position: np.ndarray,
    walls: List[Tuple[float, float, float, float]],
    collision_radius: float = 0.5
) -> bool:
    """
    Verificar si la posición colisiona con alguna pared.
    
    Args:
        position: (x, y, z)
        walls: lista de ((x1, y1, x2, y2), ...)
        collision_radius: radio de detección
    
    Returns:
        True si hay colisión, False si no
    """
    if not walls:
        return False
    
    pos_2d = position[:2]
    
    for wall in walls:
        x1, y1, x2, y2 = wall
        wall_start = np.array([x1, y1])
        wall_end = np.array([x2, y2])
        
        dist = distance_point_to_line(pos_2d, wall_start, wall_end)
        if dist < collision_radius:
            return True
    
    return False


def resolve_collision(
    position: np.ndarray,
    heading: float,
    walls: List[Tuple[float, float, float, float]],
    collision_radius: float = 0.5,
) -> Tuple[np.ndarray, float]:
    """
    Resolver colisión: mover el punto fuera de la pared (método simple: rebote).
    
    Args:
        position: (x, y, z)
        heading: ángulo actual
        walls: lista de paredes
        collision_radius: radio mínimo
    
    Returns:
        (nueva_position, nuevo_heading)
    """
    if not check_collision_with_walls(position, walls, collision_radius):
        return position, heading
    
    # Estrategia simple: retroceder en la dirección opuesta al movimiento
    # y girar hacia un ángulo diferente
    pos_2d = position[:2]
    
    # Encontrar la pared más cercana
    min_dist = float('inf')
    closest_wall = None
    closest_dist_to_line = float('inf')
    closest_normal = np.array([0.0, 1.0])
    
    for wall in walls:
        x1, y1, x2, y2 = wall
        wall_start = np.array([x1, y1])
        wall_end = np.array([x2, y2])
        
        dist = distance_point_to_line(pos_2d, wall_start, wall_end)
        if dist < min_dist:
            min_dist = dist
            closest_wall = wall
            closest_dist_to_line = dist
            
            # Calcular normal a la pared
            wall_vec = wall_end - wall_start
            wall_vec = wall_vec / (np.linalg.norm(wall_vec) + 1e-6)
            # Normal perpendicular
            wall_normal = np.array([-wall_vec[1], wall_vec[0]])
            # Asegurarse que la normal apunta hacia afuera
            closest_normal = wall_normal
    
    # Mover en dirección de la normal
    new_pos = position.copy()
    push_dist = collision_radius - closest_dist_to_line + 0.2  # margen un poco mayor
    new_pos[:2] = new_pos[:2] + push_dist * closest_normal
    
    # Girar más agresivamente para escapar (90° en dirección perpendicular a la pared)
    new_heading = heading + np.radians(90.0)
    
    return new_pos, new_heading


def get_wall_proximity(
    position: np.ndarray,
    heading: float,
    walls: List[Tuple[float, float, float, float]],
    sensing_distance: float = 5.0,
) -> Tuple[float, float]:
    """
    Detectar proximidad a paredes en la dirección forward del movimiento.
    
    Simula un "sensor de proximidad frontal" que detecta si hay una pared
    en el camino de la mosca.
    
    Args:
        position: (x, y, z) posición actual
        heading: radianes, dirección de movimiento
        walls: lista de paredes
        sensing_distance: distancia máxima de detección (mm)
    
    Returns:
        (distance_to_nearest_wall, wall_angle_offset)
        - distance_to_nearest_wall: distancia a la pared más cercana (mm)
        - wall_angle_offset: ángulo al que está la pared (-1=izquierda, 0=frente, 1=derecha)
    """
    if not walls:
        return sensing_distance, 0.0  # Sin paredes, camino libre
    
    pos_2d = position[:2]
    min_wall_dist = sensing_distance
    nearest_wall_offset = 0.0
    
    for wall in walls:
        x1, y1, x2, y2 = wall
        wall_start = np.array([x1, y1])
        wall_end = np.array([x2, y2])
        
        dist_to_wall = distance_point_to_line(pos_2d, wall_start, wall_end)
        
        # Si está dentro de rango de sensado y es más cercano
        if dist_to_wall < min_wall_dist:
            min_wall_dist = dist_to_wall
            
            # Calcular ángulo de la pared relativo al heading
            wall_vec = wall_end - wall_start
            wall_angle = np.arctan2(wall_vec[1], wall_vec[0])
            angle_diff = wall_angle - heading
            # Normalizar a [-pi, pi]
            angle_diff = np.arctan2(np.sin(angle_diff), np.cos(angle_diff))
            # Convertir a [-1, 1]: -pi/2 = izquierda (-1), 0 = frente, pi/2 = derecha (1)
            nearest_wall_offset = angle_diff / (np.pi / 2.0)
            nearest_wall_offset = np.clip(nearest_wall_offset, -1.0, 1.0)
    
    return min_wall_dist, nearest_wall_offset


def make_brain() -> ModularBrain:
    """
    Instanciar ModularBrain con sensorimotor integration.
    
    El cerebro modular integra:
    - Olfaction (controlador principal)
    - Vision (evaluador de confianza)
    - Mechanoreceptors (restricciones de obstáculos)
    
    La decisión final es una fusión coordinada, no sumaa de voces.
    
    EFECTO ESPERADO:
    - 20-25mm: ~ 0.8-0.9 (acercándose, buen impulso)
    - 10-15mm: ~ 0.9-0.95 (en estructura, máximo sostenido)  
    - 5-10mm: ~ 0.5-0.7 (cerca, empieza a frenar)
    - <5mm: ~ 0-0.3 (muy cerca, parada natural)
    
    Refs: Gomez-Marin et al. 2011, Demir et al. 2020
    """
    return ModularBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8
    )


def make_odor_field() -> OdorField:
    """
    Instanciar campo de olor Gaussiano con parámetros realistas.
    
    AJUSTE CRÍTICO: sigma = 10.0 mm (balance óptimo)
    
    Análisis:
    - sigma=8.0: Gradiente muy abrupto, forward satura a 1.0 ❌
    - sigma=12.0: Gradiente suave pero dC/dt → 0 en saturación, mosca se muere ❌
    - sigma=10.0: BALANCE - gradiente suave natural pero dC/dt suficiente ✅
    
    JUSTIFICACIÓN BIOLÓGICA (Demir et al. 2020):
    Plume width experimental ~10-15 mm
    10.0 permite:
    1. Patrón tipo campana (no saturado)
    2. Gradientes suficientes para llegar al origen
    3. Deceleration natural cuando está muy cerca
    
    Refs: Demir et al. 2020, Louis et al. 2008, Gomez-Marin et al. 2011
    """
    return OdorField(
        sources=tuple(ODOR_SOURCE),
        sigma=9.5,  # Gradientes más pronunciados para penetración
        amplitude=100.0
    )


def run_single_step(
    brain: ModularBrain,
    odor_field: OdorField,
    position: np.ndarray,
    heading: float,
    step_num: int,
    time: float,
    prev_position: np.ndarray = None,
    prev_heading: float = None,
    wall_proximity_mm: float = 999.0,
    wall_offset_angle: float = 0.0,
) -> Dict[str, Any]:
    """
    Ejecutar un paso de simulación y capturar TODO el análisis técnico.
    
    Returns: diccionario con:
      - Posición, heading, distancia, concentración
      - Sensores bilaterales (left/right/center)
      - Comandos motores (forward/turn)
      - Velocidades derivadas (speed, angular_velocity)
      - Gradientes (espacial, temporal)
      - Métricas avanzadas
    """
    pos_x, pos_y, pos_z = position
    heading_deg = np.degrees(heading)
    
    # === SENSORS BILATERALES ===
    bilateral_dist = brain.bilateral_distance
    left_angle = heading + np.pi / 2
    right_angle = heading - np.pi / 2
    
    left_pos = position + bilateral_dist * np.array([
        np.cos(left_angle), np.sin(left_angle), 0
    ])
    right_pos = position + bilateral_dist * np.array([
        np.cos(right_angle), np.sin(right_angle), 0
    ])
    
    conc_center = float(odor_field.concentration_at(position))
    conc_left = float(odor_field.concentration_at(left_pos))
    conc_right = float(odor_field.concentration_at(right_pos))
    
    # === MOTOR OUTPUT (cerebro decide) ===
    forward_cmd, turn_cmd = brain.step(odor_field, position, heading, wall_proximity_mm, wall_offset_angle)
    forward_cmd = float(forward_cmd)
    turn_cmd = float(turn_cmd)
    
    # === VELOCIDADES DERIVADAS ===
    forward_speed = forward_cmd * MAX_SPEED  # mm/s
    turn_rate = turn_cmd * MAX_TURN_RATE    # rad/s
    
    # === GRADIENTES ESPACIALES (BILATERAL) ===
    gradient_lr_raw = conc_left - conc_right
    total_conc = conc_left + conc_right + 1e-8
    gradient_lr_norm = gradient_lr_raw / total_conc
    
    # === DISTANCIA A FUENTE ===
    dist_to_source = float(np.linalg.norm(position[:2] - ODOR_SOURCE[:2]))
    
    # === VELOCIDAD LINEAL REAL (derivada numérica) ===
    linear_velocity = 0.0
    angular_velocity = 0.0
    if prev_position is not None and step_num > 0:
        displacement = np.linalg.norm(position[:2] - prev_position[:2])
        linear_velocity = displacement / DT  # mm/s
        # Angular velocity
        heading_diff = heading - prev_heading
        heading_diff = np.arctan2(np.sin(heading_diff), np.cos(heading_diff))
        angular_velocity = heading_diff / DT  # rad/s
    
    # === DISTANCIA VIAJADA EN ESTE PASO ===
    step_distance = 0.0
    if prev_position is not None:
        step_distance = float(np.linalg.norm(position[:2] - prev_position[:2]))
    
    # === ACELERACIÓN (cambio de velocidad) ===
    # velocity_mag = np.sqrt(forward_speed**2 + (turn_rate * bilateral_dist)**2)
    # Simplificado: solo forward
    velocity_mag = linear_velocity
    
    # === BRAIN DIAGNOSTICS ===
    brain_diag = brain.get_diagnostics() if hasattr(brain, "get_diagnostics") else {}
    
    # === CONCENTRACIÓN RELATIVA A MÁXIMO OBSERVADO ===
    # (útil para normalizar después del análisis)
    conc_max_observed = brain_diag.get("max_concentration", conc_center)
    conc_normalized = conc_center / (conc_max_observed + 1e-8)
    
    return {
        # Tiempo y paso
        "step": int(step_num),
        "time": float(time),
        
        # Posición y orientación
        "position_x": float(pos_x),
        "position_y": float(pos_y),
        "position_z": float(pos_z),
        "position_list": position.copy().tolist(),
        "heading_rad": float(heading),
        "heading_deg": float(heading_deg),
        
        # Distancias
        "dist_to_source": float(dist_to_source),
        "step_distance": float(step_distance),
        
        # Sensores bilaterales
        "conc_center": float(conc_center),
        "conc_left": float(conc_left),
        "conc_right": float(conc_right),
        "conc_normalized": float(conc_normalized),
        "sensor_left_pos": left_pos.tolist(),
        "sensor_right_pos": right_pos.tolist(),
        
        # Gradientes
        "gradient_lr_raw": float(gradient_lr_raw),
        "gradient_lr_norm": float(gradient_lr_norm),
        "gradient_sign": float(np.sign(gradient_lr_raw)),
        
        # Comandos motores (sin escalar)
        "forward_cmd": float(forward_cmd),
        "turn_cmd": float(turn_cmd),
        
        # Velocidades (escaladas por MAX_SPEED y MAX_TURN_RATE)
        "forward_speed_mm_s": float(forward_speed),
        "turn_rate_rad_s": float(turn_rate),
        "linear_velocity_mm_s": float(linear_velocity),
        "angular_velocity_rad_s": float(angular_velocity),
        
        # Brain diagnostics
        "brain_mean_conc": float(brain_diag.get("mean_concentration", 0.0)),
        "brain_max_conc": float(brain_diag.get("max_concentration", 0.0)),
        "brain_min_conc": float(brain_diag.get("min_concentration", 0.0)),
        
        # Wall/obstacle diagnostics (inicializados aquí, se actualizan en run_with_obstacles)
        "wall_proximity_mm": float(999.0),
        "wall_offset_angle": float(0.0),
        "collision": False,
        "collision_count": 0,
    }


def compute_technical_analysis(
    step_data: List[Dict[str, Any]],
    positions: np.ndarray,
    headings: np.ndarray,
) -> Dict[str, Any]:
    """
    Análisis técnico avanzado: convergencia, oscilaciones, métricas derivadas.
    NO se imprime en consola; solo se guarda en JSON.
    """
    if not step_data:
        return {}
    
    times = np.array([s["time"] for s in step_data])
    distances = np.array([s["dist_to_source"] for s in step_data])
    concs = np.array([s["conc_center"] for s in step_data])
    forward_cmds = np.array([s["forward_cmd"] for s in step_data])
    turn_cmds = np.array([s["turn_cmd"] for s in step_data])
    gradients = np.array([s["gradient_lr_norm"] for s in step_data])
    lin_vels = np.array([s["linear_velocity_mm_s"] for s in step_data])
    ang_vels = np.array([s["angular_velocity_rad_s"] for s in step_data])
    
    # === CONVERGENCIA ===
    dist_change = distances[-1] - distances[0]
    convergence_rate = dist_change / (times[-1] + 1e-8)  # mm/s converging (negative = approaching)
    
    # === OSCILACIONES ===
    # Detectar oscilaciones en distancia usando detección de picos
    peaks, _ = signal.find_peaks(distances)
    troughs, _ = signal.find_peaks(-distances)
    num_oscillations = len(peaks) + len(troughs)
    
    # === ESTADÍSTICAS MOTORAS ===
    forward_active_ratio = float(np.sum(forward_cmds > 0.1) / len(forward_cmds))  # % pasos con forward > 0.1
    turn_bias = float(np.mean(turn_cmds))  # sesgo de giro (+left, -right)
    turn_std = float(np.std(turn_cmds))
    
    # === ESTADÍSTICAS DE CONCENTRACIÓN ===
    conc_std = float(np.std(concs))
    conc_range = float(np.max(concs) - np.min(concs))
    conc_gradient_corr = float(np.corrcoef(concs, np.abs(gradients))[0, 1]) if len(concs) > 2 else 0.0
    
    # === EFICIENCIA ===
    total_distance_mm = float(np.sum([
        np.linalg.norm(positions[i+1][:2] - positions[i][:2])
        for i in range(len(positions)-1)
    ]))
    efficiency = (distances[0] - distances[-1]) / (total_distance_mm + 1e-8) if total_distance_mm > 0 else 0.0
    
    # === VELOCIDAD PROMEDIO ===
    mean_linear_vel = float(np.mean(lin_vels))
    mean_angular_vel = float(np.mean(np.abs(ang_vels)))
    
    # === GRADIENTE ===
    gradient_std = float(np.std(gradients))
    
    # === COMPORTAMIENTO DE ACERCAMIENTO ===
    # Dividir la trayectoria en fases
    min_dist = np.min(distances)
    min_idx = np.argmin(distances)
    
    # Fase 1: antes de mínimo; Fase 2: después de mínimo
    if min_idx > 0:
        approach_phase_dist_change = distances[min_idx] - distances[0]
        approach_phase_time = times[min_idx]
    else:
        approach_phase_dist_change = 0.0
        approach_phase_time = 0.0
    
    if min_idx < len(distances) - 1:
        retreat_phase_dist_change = distances[-1] - distances[min_idx]
        retreat_phase_time = times[-1] - times[min_idx]
    else:
        retreat_phase_dist_change = 0.0
        retreat_phase_time = 0.0
    
    return {
        "distance_metrics": {
            "initial_distance_mm": float(distances[0]),
            "final_distance_mm": float(distances[-1]),
            "min_distance_mm": float(min_dist),
            "min_distance_step": int(min_idx),
            "total_distance_change_mm": float(dist_change),
            "convergence_rate_mm_s": float(convergence_rate),
            "efficiency_ratio": float(efficiency),
        },
        "oscillation_metrics": {
            "num_oscillations": int(num_oscillations),
            "num_peaks": int(len(peaks)),
            "num_troughs": int(len(troughs)),
        },
        "motor_metrics": {
            "forward_cmd_mean": float(np.mean(forward_cmds)),
            "forward_cmd_std": float(np.std(forward_cmds)),
            "forward_active_ratio": float(forward_active_ratio),
            "turn_cmd_mean": float(turn_bias),
            "turn_cmd_std": float(turn_std),
            "turn_cmd_max": float(np.max(np.abs(turn_cmds))),
        },
        "sensory_metrics": {
            "concentration_mean": float(np.mean(concs)),
            "concentration_std": float(conc_std),
            "concentration_range": float(conc_range),
            "gradient_mean": float(np.mean(np.abs(gradients))),
            "gradient_std": float(gradient_std),
            "conc_gradient_correlation": float(conc_gradient_corr),
        },
        "velocity_metrics": {
            "linear_velocity_mean_mm_s": float(mean_linear_vel),
            "linear_velocity_max_mm_s": float(np.max(lin_vels)),
            "angular_velocity_mean_rad_s": float(mean_angular_vel),
            "angular_velocity_max_rad_s": float(np.max(np.abs(ang_vels))),
        },
        "phase_analysis": {
            "approach_phase_distance_change_mm": float(approach_phase_dist_change),
            "approach_phase_time_s": float(approach_phase_time),
            "retreat_phase_distance_change_mm": float(retreat_phase_dist_change),
            "retreat_phase_time_s": float(retreat_phase_time),
        },
    }


def save_outputs(
    outdir: Path,
    timestamp: str,
    step_data: List[Dict[str, Any]],
    positions: np.ndarray,
    headings: np.ndarray,
    technical_analysis: Dict[str, Any],
    fig: plt.Figure = None,
):
    """
    Guardar todos los datos: JSON (completo + técnico), CSV, NPZ, PNG.
    """
    json_path = outdir / f"brain_analysis_{timestamp}.json"
    csv_path = outdir / f"brain_analysis_{timestamp}.csv"
    npz_path = outdir / f"brain_analysis_{timestamp}.npz"
    technical_path = outdir / f"brain_technical_analysis_{timestamp}.json"
    png_path = outdir / f"brain_analysis_{timestamp}.png"
    
    # === JSON (completo con todos los datos de pasos) ===
    full_data = {
        "timestamp": timestamp,
        "simulation_config": {
            "num_steps": NUM_STEPS,
            "dt_s": DT,
            "max_speed_mm_s": MAX_SPEED,
            "max_turn_rate_rad_s": MAX_TURN_RATE,
        },
        "brain_config": {
            "bilateral_distance_mm": 1.2,
            "forward_scale": 1.0,
            "turn_scale": 0.8,
            "temporal_gradient_gain": 50.0,
        },
        "odor_field_config": {
            "source_position": ODOR_SOURCE.tolist(),
            "sigma_mm": 8.0,
            "amplitude": 100.0,
        },
        "initial_conditions": {
            "position_mm": positions[0].tolist(),
            "heading_rad": float(headings[0]),
            "heading_deg": float(np.degrees(headings[0])),
        },
        "step_data": step_data,
    }
    with open(json_path, "w") as f:
        json.dump(full_data, f, indent=2)
    print(f"[OK] Saved full data: {json_path}")
    
    # === TECHNICAL ANALYSIS (separado, para lectura rápida) ===
    with open(technical_path, "w") as f:
        json.dump(technical_analysis, f, indent=2)
    print(f"[OK] Saved technical analysis: {technical_path}")
    
    # === CSV (aplanado, para análisis rápido en Excel/pandas) ===
    df = pd.DataFrame(step_data)
    # Convertir listas a strings para CSV
    for col in ["position_list", "sensor_left_pos", "sensor_right_pos"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: "|".join(f"{x:.6f}" for x in v))
    df.to_csv(csv_path, index=False)
    print(f"[OK] Saved CSV: {csv_path}")
    
    # === NPZ (arrays numéricos comprimidos para análisis rápido) ===
    try:
        times = np.array([s["time"] for s in step_data])
        concs = np.array([s["conc_center"] for s in step_data])
        dists = np.array([s["dist_to_source"] for s in step_data])
        fwd_cmds = np.array([s["forward_cmd"] for s in step_data])
        turn_cmds = np.array([s["turn_cmd"] for s in step_data])
        grads = np.array([s["gradient_lr_norm"] for s in step_data])
        lin_vels = np.array([s["linear_velocity_mm_s"] for s in step_data])
        
        np.savez_compressed(
            npz_path,
            positions=positions,
            headings=headings,
            times=times,
            concentrations=concs,
            distances=dists,
            forward_commands=fwd_cmds,
            turn_commands=turn_cmds,
            gradients=grads,
            linear_velocities=lin_vels,
        )
        print(f"[OK] Saved NPZ: {npz_path}")
    except Exception as e:
        print(f"[WARN] Could not save NPZ: {e}")
    
    # === PNG ===
    if fig is not None:
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        print(f"[OK] Saved PNG: {png_path}")


def plot_results(
    step_data: List[Dict[str, Any]],
    positions: np.ndarray,
    headings: np.ndarray,
    technical_analysis: Dict[str, Any],
    walls: List[Tuple[float, float, float, float]] = None,
) -> plt.Figure:
    """
    Gráficos comprehensive: trayectoria, distancia, concentración, comandos, velocidades, etc.
    Si walls es no-None, dibuja las paredes en el gráfico de trayectoria.
    """
    if walls is None:
        walls = []
    
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(4, 4, hspace=0.4, wspace=0.35)
    
    times = np.array([s["time"] for s in step_data])
    distances = np.array([s["dist_to_source"] for s in step_data])
    concs = np.array([s["conc_center"] for s in step_data])
    forward_cmds = np.array([s["forward_cmd"] for s in step_data])
    turn_cmds = np.array([s["turn_cmd"] for s in step_data])
    lin_vels = np.array([s["linear_velocity_mm_s"] for s in step_data])
    ang_vels = np.array([s["angular_velocity_rad_s"] for s in step_data])
    gradients = np.array([s["gradient_lr_norm"] for s in step_data])
    steps = np.arange(1, len(step_data) + 1)
    
    # --- Trajectory (2D) ---
    ax = fig.add_subplot(gs[0:2, 0:2])
    x_min, x_max = min(positions[:,0].min(), ODOR_SOURCE[0] - 25), max(positions[:,0].max(), ODOR_SOURCE[0] + 25)
    y_min, y_max = min(positions[:,1].min(), ODOR_SOURCE[1] - 25), max(positions[:,1].max(), ODOR_SOURCE[1] + 25)
    x_range = np.linspace(x_min, x_max, 100)
    y_range = np.linspace(y_min, y_max, 100)
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.zeros_like(X)
    odor_field = make_odor_field()
    for i in range(len(x_range)):
        for j in range(len(y_range)):
            Z[j, i] = odor_field.concentration_at(np.array([X[j, i], Y[j, i], ODOR_Z_SAMPLE]))
    
    contour = ax.contourf(X, Y, Z, levels=20, cmap='YlOrRd', alpha=0.8)
    plt.colorbar(contour, ax=ax, label='Odor Conc')
    ax.plot(positions[:, 0], positions[:, 1], 'b-', linewidth=2, alpha=0.8, label='Path')
    ax.plot(positions[0, 0], positions[0, 1], 'go', markersize=12, label='Start', zorder=5)
    ax.plot(positions[-1, 0], positions[-1, 1], 'rs', markersize=12, label='End', zorder=5)
    ax.plot(ODOR_SOURCE[0], ODOR_SOURCE[1], 'r*', markersize=25, label='Source', zorder=6)
    
    # Dibujar paredes (obstáculos) si existen
    if walls:
        for i, wall in enumerate(walls):
            x1, y1, x2, y2 = wall
            ax.plot([x1, x2], [y1, y2], 'k-', linewidth=5, alpha=0.9, zorder=10)
            ax.plot([x1, x2], [y1, y2], 'yellow', linewidth=3, linestyle='--', alpha=0.7, 
                   zorder=11, label='Wall' if i == 0 else '')
    
    for i in range(0, len(positions), max(1, len(positions)//20)):
        dx, dy = 2 * np.cos(headings[i]), 2 * np.sin(headings[i])
        ax.arrow(positions[i, 0], positions[i, 1], dx, dy, head_width=0.5, head_length=0.3, fc='blue', ec='blue', alpha=0.4)
    
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_title(f'2D Trajectory ({len(step_data)} steps)')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.2)
    ax.set_aspect('equal')
    
    # --- Distance ---
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(steps, distances, 'b-o', linewidth=2, markersize=4)
    ax.axhline(y=distances[0], color='g', linestyle='--', alpha=0.6, linewidth=2)
    ax.set_xlabel('Step')
    ax.set_ylabel('Distance (mm)')
    ax.set_title('Distance to Source')
    ax.grid(True, alpha=0.3)
    
    # --- Concentration ---
    ax = fig.add_subplot(gs[0, 3])
    ax.plot(steps, concs, 'o-', color='orange', linewidth=2, markersize=4)
    ax.set_xlabel('Step')
    ax.set_ylabel('Concentration')
    ax.set_title('Odor Concentration')
    ax.grid(True, alpha=0.3)
    
    # --- Gradient ---
    ax = fig.add_subplot(gs[1, 2])
    ax.plot(steps, gradients, 'o-', color='purple', linewidth=2, markersize=4)
    ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax.set_xlabel('Step')
    ax.set_ylabel('Gradient (L-R normalized)')
    ax.set_title('Bilateral Gradient')
    ax.grid(True, alpha=0.3)
    
    # --- Heading ---
    ax = fig.add_subplot(gs[1, 3])
    heading_deg = np.degrees(headings)
    ax.plot(steps, heading_deg[:-1], 'o-', color='brown', linewidth=2, markersize=4)
    ax.set_xlabel('Step')
    ax.set_ylabel('Heading (degrees)')
    ax.set_title('Orientation')
    ax.grid(True, alpha=0.3)
    
    # --- Forward Command ---
    ax = fig.add_subplot(gs[2, 0])
    ax.plot(steps, forward_cmds, 'b-', linewidth=2)
    ax.fill_between(steps, forward_cmds, alpha=0.3, color='blue')
    ax.set_xlabel('Step')
    ax.set_ylabel('Forward Cmd')
    ax.set_title('Forward Motor Command')
    ax.grid(True, alpha=0.3)
    
    # --- Turn Command ---
    ax = fig.add_subplot(gs[2, 1])
    ax.plot(steps, turn_cmds, 'r-', linewidth=2)
    ax.axhline(0, color='k', linestyle='-', alpha=0.3)
    ax.set_xlabel('Step')
    ax.set_ylabel('Turn Cmd')
    ax.set_title('Turn Motor Command')
    ax.grid(True, alpha=0.3)
    
    # --- Linear Velocity ---
    ax = fig.add_subplot(gs[2, 2])
    ax.plot(steps, lin_vels, 'g-', linewidth=2)
    ax.fill_between(steps, lin_vels, alpha=0.3, color='green')
    ax.set_xlabel('Step')
    ax.set_ylabel('Linear Vel (mm/s)')
    ax.set_title('Linear Velocity')
    ax.grid(True, alpha=0.3)
    
    # --- Angular Velocity ---
    ax = fig.add_subplot(gs[2, 3])
    ax.plot(steps, ang_vels, 'c-', linewidth=2)
    ax.axhline(0, color='k', linestyle='-', alpha=0.3)
    ax.set_xlabel('Step')
    ax.set_ylabel('Angular Vel (rad/s)')
    ax.set_title('Angular Velocity')
    ax.grid(True, alpha=0.3)
    
    # --- Motor Command Distribution ---
    ax = fig.add_subplot(gs[3, 0])
    ax.hist(forward_cmds, bins=20, color='blue', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Forward Cmd')
    ax.set_ylabel('Count')
    ax.set_title('Forward Cmd Distribution')
    ax.grid(True, alpha=0.3)
    
    # --- Turn Command Distribution ---
    ax = fig.add_subplot(gs[3, 1])
    ax.hist(turn_cmds, bins=20, color='red', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Turn Cmd')
    ax.set_ylabel('Count')
    ax.set_title('Turn Cmd Distribution')
    ax.grid(True, alpha=0.3)
    
    # --- Conc vs Distance (scatter) ---
    ax = fig.add_subplot(gs[3, 2])
    ax.scatter(distances, concs, c=steps, cmap='viridis', s=30, alpha=0.7)
    ax.set_xlabel('Distance (mm)')
    ax.set_ylabel('Concentration')
    ax.set_title('Conc vs Distance')
    ax.grid(True, alpha=0.3)
    cbar = plt.colorbar(ax.scatter(distances, concs, c=steps, cmap='viridis', s=30, alpha=0.7), ax=ax)
    cbar.set_label('Step')
    
    # --- Technical Summary (text) ---
    ax = fig.add_subplot(gs[3, 3])
    ax.axis('off')
    
    ta = technical_analysis
    summary_text = f"""TECHNICAL SUMMARY
{'─'*30}
Distance:
  Initial: {ta['distance_metrics']['initial_distance_mm']:.2f} mm
  Final: {ta['distance_metrics']['final_distance_mm']:.2f} mm
  Min: {ta['distance_metrics']['min_distance_mm']:.2f} mm
  Change: {ta['distance_metrics']['total_distance_change_mm']:.2f} mm

Motor:
  Fwd mean: {ta['motor_metrics']['forward_cmd_mean']:.3f}
  Turn mean: {ta['motor_metrics']['turn_cmd_mean']:.3f}
  Turn std: {ta['motor_metrics']['turn_cmd_std']:.3f}

Velocity:
  Lin mean: {ta['velocity_metrics']['linear_velocity_mean_mm_s']:.2f} mm/s
  Ang mean: {ta['velocity_metrics']['angular_velocity_mean_rad_s']:.3f} rad/s

Convergence:
  Rate: {ta['distance_metrics']['convergence_rate_mm_s']:.4f} mm/s
  Efficiency: {ta['distance_metrics']['efficiency_ratio']:.3f}
"""
    ax.text(0.02, 0.98, summary_text, transform=ax.transAxes, fontsize=8.5, va='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    fig.suptitle(f'BRAIN CHEMOTAXIS TEST - {len(step_data)} steps', fontsize=14, fontweight='bold')
    return fig


def main():
    """Main entry point - hardcoded para test."""
    
    print("\n" + "="*80)
    if ENABLE_OBSTACLES:
        print("BRAIN ISOLATION TEST - CHEMOTAXIS WITH OBSTACLES")
        initial_position = INITIAL_POS_OBSTACLES.copy()
        initial_heading = INITIAL_HEADING_OBSTACLES
        walls = OBSTACLE_WALLS
    else:
        print("BRAIN ISOLATION TEST - CHEMOTAXIS (NORMAL)")
        initial_position = INITIAL_POS_NORMAL.copy()
        initial_heading = INITIAL_HEADING_NORMAL
        walls = []
    print("="*80)
    print(f"Steps: {NUM_STEPS}, DT: {DT}s, MAX_SPEED: {MAX_SPEED} mm/s, MAX_TURN: {MAX_TURN_RATE} rad/s")
    print(f"Obstacles: {ENABLE_OBSTACLES}")
    print(f"Output base: {PROJECT_ROOT / OUTPUT_BASE}")
    print("="*80)
    
    # Initialize
    brain = make_brain()
    odor_field = make_odor_field()
    outdir, timestamp = create_output_dir()
    
    # Run simulation
    step_data, positions, headings = run_simulation(
        brain, 
        odor_field, 
        initial_position, 
        initial_heading, 
        NUM_STEPS,
        enable_obstacles=ENABLE_OBSTACLES,
        walls=walls,
        collision_radius=OBSTACLE_RADIUS,
        verbose=VERBOSE
    )
    
    # Technical analysis
    technical_analysis = compute_technical_analysis(step_data, positions, headings)
    
    # Plot
    fig = plot_results(step_data, positions, headings, technical_analysis, walls=walls)
    
    # Save all outputs
    save_outputs(outdir, timestamp, step_data, positions, headings, technical_analysis, fig=fig)
    
    # Console summary
    ta = technical_analysis
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    print(f"Obstacles: {ENABLE_OBSTACLES}")
    print(f"Steps executed: {len(step_data)}")
    print(f"Duration: {step_data[-1]['time']:.3f}s")
    print(f"Distance: {ta['distance_metrics']['initial_distance_mm']:.2f}mm -> "
          f"{ta['distance_metrics']['final_distance_mm']:.2f}mm (min: {ta['distance_metrics']['min_distance_mm']:.2f}mm)")
    print(f"Convergence rate: {ta['distance_metrics']['convergence_rate_mm_s']:.4f} mm/s")
    print(f"Motor activity: fwd_mean={ta['motor_metrics']['forward_cmd_mean']:.3f}, "
          f"turn_mean={ta['motor_metrics']['turn_cmd_mean']:.3f}")
    
    if ENABLE_OBSTACLES:
        collision_count = sum(1 for s in step_data if s.get("collision", False))
        print(f"Colisiones totales: {collision_count}")
    
    print("\nAll detailed data saved to:")
    print(f"  {outdir}")
    print("="*80 + "\n")
    
    if plt:
        plt.show()


def main(argv=None):
    """Main entry point - hardcoded para test."""
    
    print("\n" + "="*80)
    if ENABLE_OBSTACLES:
        print("BRAIN ISOLATION TEST - CHEMOTAXIS WITH OBSTACLES")
        initial_position = INITIAL_POS_OBSTACLES.copy()
        initial_heading = INITIAL_HEADING_OBSTACLES
        walls = OBSTACLE_WALLS
    else:
        print("BRAIN ISOLATION TEST - CHEMOTAXIS (NORMAL)")
        initial_position = INITIAL_POS_NORMAL.copy()
        initial_heading = INITIAL_HEADING_NORMAL
        walls = []
    print("="*80)
    print(f"Steps: {NUM_STEPS}, DT: {DT}s, MAX_SPEED: {MAX_SPEED} mm/s, MAX_TURN: {MAX_TURN_RATE} rad/s")
    print(f"Obstacles: {ENABLE_OBSTACLES}")
    print(f"Output base: {PROJECT_ROOT / OUTPUT_BASE}")
    print("="*80)
    
    # Initialize
    brain = make_brain()
    odor_field = make_odor_field()
    outdir, timestamp = create_output_dir()
    
    # Run simulation
    step_data, positions, headings = run_simulation(
        brain, 
        odor_field, 
        initial_position, 
        initial_heading, 
        NUM_STEPS,
        enable_obstacles=ENABLE_OBSTACLES,
        walls=walls,
        collision_radius=OBSTACLE_RADIUS,
        verbose=VERBOSE
    )
    
    # Technical analysis
    technical_analysis = compute_technical_analysis(step_data, positions, headings)
    
    # Plot
    fig = plot_results(step_data, positions, headings, technical_analysis, walls=walls)
    
    # Save all outputs
    save_outputs(outdir, timestamp, step_data, positions, headings, technical_analysis, fig=fig)
    
    # Console summary
    ta = technical_analysis
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    print(f"Obstacles: {ENABLE_OBSTACLES}")
    print(f"Steps executed: {len(step_data)}")
    print(f"Duration: {step_data[-1]['time']:.3f}s")
    print(f"Distance: {ta['distance_metrics']['initial_distance_mm']:.2f}mm -> "
          f"{ta['distance_metrics']['final_distance_mm']:.2f}mm (min: {ta['distance_metrics']['min_distance_mm']:.2f}mm)")
    print(f"Convergence rate: {ta['distance_metrics']['convergence_rate_mm_s']:.4f} mm/s")
    print(f"Motor activity: fwd_mean={ta['motor_metrics']['forward_cmd_mean']:.3f}, "
          f"turn_mean={ta['motor_metrics']['turn_cmd_mean']:.3f}")
    
    if ENABLE_OBSTACLES:
        collision_count = sum(1 for s in step_data if s.get("collision", False))
        print(f"Colisiones totales: {collision_count}")
    
    print("\nAll detailed data saved to:")
    print(f"  {outdir}")
    print("="*80 + "\n")
    
    if plt:
        plt.show()


def run_simulation(
    brain: ModularBrain,
    odor_field: OdorField,
    initial_position: np.ndarray,
    initial_heading: float,
    num_steps: int,
    enable_obstacles: bool = False,
    walls: List[Tuple[float, float, float, float]] = None,
    collision_radius: float = 0.5,
    verbose: bool = True,
) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    """
    Ejecutar simulación de chemotaxis con o sin obstáculos.
    
    Args:
        brain: ModularBrain
        odor_field: OdorField
        initial_position: np.ndarray (x, y, z)
        initial_heading: float (radianes)
        num_steps: int
        enable_obstacles: bool - si True, usar detección de colisiones
        walls: List[(x1, y1, x2, y2), ...] - paredes como líneas
        collision_radius: float - radio de detección de colisiones
        verbose: bool
    
    Returns:
        (step_data, positions, headings)
    """
    if walls is None:
        walls = []
    
    position = initial_position.copy().astype(float)
    heading = float(initial_heading)
    
    positions = [position.copy()]
    headings = [heading]
    step_data: List[Dict[str, Any]] = []
    collision_count = 0
    
    if verbose:
        mode_str = "[OBSTACLES]" if enable_obstacles else "[NORMAL]"
        print(f"\n{mode_str} Iniciando simulación: {num_steps} pasos, DT={DT}s")
        print(f"Posición inicial: ({position[0]:.2f}, {position[1]:.2f})")
        print(f"Heading inicial: {np.degrees(heading):.1f}°")
        print(f"Fuente en: ({ODOR_SOURCE[0]:.2f}, {ODOR_SOURCE[1]:.2f})")
        if enable_obstacles and walls:
            print(f"Número de paredes: {len(walls)}")
            for i, (x1, y1, x2, y2) in enumerate(walls):
                print(f"  Pared {i+1}: ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
        print()
    
    for step in range(num_steps):
        time = step * DT
        prev_pos = positions[-1].copy() if len(positions) > 1 else None
        prev_head = headings[-1] if len(headings) > 1 else None
        
        # SENSOR DE PROXIMIDAD A PAREDES (solo si están habilitadas)
        if enable_obstacles and walls:
            wall_proximity, wall_offset = get_wall_proximity(position, heading, walls, OBSTACLE_SENSING_DISTANCE)
        else:
            wall_proximity = 999.0  # Sin paredes
            wall_offset = 0.0
        
        # Ejecutar paso y capturar datos
        record = run_single_step(
            brain, odor_field, position, heading, step, time,
            prev_position=prev_pos, prev_heading=prev_head,
            wall_proximity_mm=wall_proximity,
            wall_offset_angle=wall_offset
        )
        
        # Actualizar posición y heading física (integración Euler)
        forward_speed = record["forward_speed_mm_s"]
        turn_rate = record["turn_rate_rad_s"]
        
        heading += turn_rate * DT
        heading = np.arctan2(np.sin(heading), np.cos(heading))  # normalize
        
        position[0] += forward_speed * np.cos(heading) * DT
        position[1] += forward_speed * np.sin(heading) * DT
        
        # CHEQUEO DE COLISIONES (solo si están habilitadas)
        if enable_obstacles and walls:
            wall_proximity, wall_offset = get_wall_proximity(position, heading, walls, OBSTACLE_SENSING_DISTANCE)
            record["wall_proximity_mm"] = wall_proximity
            record["wall_offset_angle"] = wall_offset  # -1=izquierda, 0=frente, 1=derecha
            
            if check_collision_with_walls(position, walls, collision_radius):
                collision_count += 1
                position, heading = resolve_collision(position, heading, walls, collision_radius)
                record["collision"] = True
                record["collision_count"] = collision_count
                if verbose and collision_count % 10 == 0:
                    print(f"  >>> COLISIÓN #{collision_count} en paso {step+1}, "
                          f"posición ({position[0]:.2f}, {position[1]:.2f}), "
                          f"proximidad={wall_proximity:.2f}mm")
            else:
                record["collision"] = False
                record["collision_count"] = collision_count
        
        step_data.append(record)
        positions.append(position.copy())
        headings.append(heading)
        
        # Check reach
        if record["dist_to_source"] < 2.0:
            if verbose:
                msg = f"\n  >>> FUENTE ALCANZADA en paso {step+1}, tiempo {time:.3f}s, distancia {record['dist_to_source']:.3f} mm"
                if enable_obstacles:
                    msg += f", colisiones totales: {collision_count}"
                print(msg)
        
        # Logging
        if verbose and ((step + 1) % max(1, LOG_EVERY) == 0 or step == 0):
            log_str = f"  Step {step+1:5d}: pos=({position[0]:7.2f},{position[1]:7.2f}) | " \
                      f"dist={record['dist_to_source']:6.2f}mm | conc={record['conc_center']:7.1f} | " \
                      f"fwd={record['forward_cmd']:5.3f} turn={record['turn_cmd']:6.3f}"
            if enable_obstacles and walls:
                log_str += f" | wall={wall_proximity:.1f}mm"
                if record.get("collision", False):
                    log_str += " [COLLISION]"
            print(log_str)
    
    if verbose and enable_obstacles:
        print(f"\n[OBSTACLES] Simulación completada. Total colisiones: {collision_count}")
    
    return step_data, np.array(positions), np.array(headings)


if __name__ == "__main__":
    main()
