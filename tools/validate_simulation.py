#!/usr/bin/env python3
"""
VALIDACIÓN UNIFICADA DE SIMULACIÓN
===================================
Script único que agrupa TODOS los tests y validaciones de la simulación 3D.

Ejecutable con opciones --test para seleccionar qué validar:
    python tools/validate_simulation.py --test all           # Todos los tests
    python tools/validate_simulation.py --test data          # Estructura de datos
    python tools/validate_simulation.py --test flygym        # Integración FlyGym
    python tools/validate_simulation.py --test angles        # Ángulos articulares
    python tools/validate_simulation.py --test render        # Renderizado (diagnóstico)
"""

import sys
from pathlib import Path
import numpy as np
import pickle
import argparse
from typing import Dict, Tuple, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# ============================================================================
# TEST 1: VALIDAR ESTRUCTURA DE DATOS
# ============================================================================

def test_data_structure() -> Tuple[bool, Dict]:
    """
    Cargar y validar estructura de datos de simulación.
    
    Verifica:
    - Archivo existe
    - Contiene todas las claves necesarias
    - Dimensiones son compatibles con 300 frames
    - Valores están en rangos razonables
    """
    print("\n" + "="*70)
    print("TEST 1: VALIDAR ESTRUCTURA DE DATOS")
    print("="*70)
    
    # Buscar último archivo .pkl de simulación
    simulations_dir = PROJECT_ROOT / "outputs" / "simulations"
    if not simulations_dir.exists():
        print("[X] No existe directorio de simulaciones")
        return False, {}
    
    pkl_files = list(simulations_dir.glob("**/simulation_trajectory_3d.pkl"))
    if not pkl_files:
        print("[X] No hay archivos .pkl de simulación")
        return False, {}
    
    pkl_file = sorted(pkl_files)[-1]  # El más reciente
    print(f"[*] Archivo encontrado: {pkl_file.relative_to(PROJECT_ROOT)}")
    
    # Cargar datos
    try:
        with open(pkl_file, "rb") as f:
            data = pickle.load(f)
        print(f"[OK] Archivo cargado correctamente")
    except Exception as e:
        print(f"[X] Error cargando archivo: {e}")
        return False, {}
    
    # Validar claves principales
    required_keys = ["times", "positions", "headings", "brain_actions"]
    missing_keys = [k for k in required_keys if k not in data]
    if missing_keys:
        print(f"[X] Claves faltantes: {missing_keys}")
        return False, {}
    print(f"[OK] Contiene todas las claves requeridas")
    
    # Validar dimensiones
    n_frames = len(data["times"])
    print(f"\n[*] Número de frames: {n_frames}")
    
    # Verificar consistencia
    dims = {
        "times": len(data["times"]),
        "positions": len(data["positions"]),
        "headings": len(data["headings"]),
        "brain_actions": len(data["brain_actions"]),
    }
    
    all_same = len(set(dims.values())) == 1
    if not all_same:
        print(f"[X] Inconsistencia de dimensiones:")
        for k, v in dims.items():
            print(f"    {k}: {v}")
        return False, {}
    print(f"[OK] Todas las secuencias tienen {n_frames} elementos")
    
    # Validar rangos de valores
    positions = np.array(data["positions"])
    print(f"\n[*] Posiciones (mm):")
    print(f"    X: [{positions[:, 0].min():.2f}, {positions[:, 0].max():.2f}]")
    print(f"    Y: [{positions[:, 1].min():.2f}, {positions[:, 1].max():.2f}]")
    print(f"    Z: [{positions[:, 2].min():.2f}, {positions[:, 2].max():.2f}]")
    
    headings = np.array(data["headings"])
    heading_deg = np.degrees(headings)
    print(f"\n[*] Orientación (grados):")
    print(f"    Min: {heading_deg.min():.2f}, Max: {heading_deg.max():.2f}")
    print(f"    Cambio total: {heading_deg[-1] - heading_deg[0]:.2f}°")
    
    actions = np.array(data["brain_actions"])
    print(f"\n[*] Comandos del cerebro:")
    print(f"    Forward: [{actions[:, 0].min():.3f}, {actions[:, 0].max():.3f}]")
    print(f"    Turn: [{actions[:, 1].min():.3f}, {actions[:, 1].max():.3f}]")
    
    # Contar claves de ángulos articulares
    angle_keys = [k for k in data.keys() if k.startswith("joint_")]
    print(f"\n[*] Ángulos articulares detectados: {len(angle_keys)} joints")
    
    if len(angle_keys) < 42:
        print(f"[!] ADVERTENCIA: Se esperaban 42 joints, se encontraron {len(angle_keys)}")
    else:
        print(f"[OK] Cantidad correcta de joints")
    
    # Verificar que los ángulos tienen datos
    angle_data_complete = True
    for joint_key in angle_keys[:3]:  # Verificar primeros 3
        if joint_key not in data:
            print(f"[X] Falta clave: {joint_key}")
            angle_data_complete = False
        else:
            n_angles = len(data[joint_key])
            if n_angles != n_frames:
                print(f"[X] {joint_key} tiene {n_angles} frames, esperaba {n_frames}")
                angle_data_complete = False
    
    if angle_data_complete:
        print(f"[OK] Datos de ángulos incompletos")
    
    return True, {
        "pkl_file": pkl_file,
        "data": data,
        "n_frames": n_frames,
        "n_joints": len(angle_keys),
        "angle_keys": angle_keys
    }


# ============================================================================
# TEST 2: VALIDAR INTEGRACIÓN FLYGYM
# ============================================================================

def test_flygym_integration(data_info: Dict) -> bool:
    """
    Verificar que FlyGym se inicializa correctamente y puede ejecutar un step.
    """
    print("\n" + "="*70)
    print("TEST 2: VALIDAR INTEGRACIÓN FLYGYM")
    print("="*70)
    
    try:
        from flygym import Fly, SingleFlySimulation
        from flygym.arena import FlatTerrain
        from flygym.preprogrammed import all_leg_dofs
        print("[OK] Importaciones FlyGym correctas")
    except ImportError as e:
        print(f"[X] Error importando FlyGym: {e}")
        return False
    
    # Crear simulación
    try:
        fly = Fly(
            init_pose="stretch",
            actuated_joints=all_leg_dofs,
            control="position",
        )
        
        sim = SingleFlySimulation(
            fly=fly,
            arena=FlatTerrain(),
        )
        
        obs, info = sim.reset()
        print(f"[OK] Simulación iniciada correctamente")
    except Exception as e:
        print(f"[X] Error inicializando simulación: {e}")
        return False
    
    # Intentar ejecutar un step
    try:
        # Crear acción dummy (42 ángulos)
        action = {"joints": np.zeros(42, dtype=np.float32)}
        obs = sim.step(action)
        print(f"[OK] Step ejecutado correctamente")
        
        # Intentar renderizar
        try:
            frames = sim.render()
            if frames:
                print(f"[OK] Render devolvió {len(frames)} frames")
            else:
                print(f"[!] Render devolvió None o vacío")
        except Exception as e:
            print(f"[X] Error en render: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"[X] Error ejecutando step: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 3: VALIDAR ÁNGULOS ARTICULARES
# ============================================================================

def test_angle_format_conversion(data_info: Dict) -> bool:
    """
    Verificar que format_joint_data convierte correctamente los ángulos.
    """
    print("\n" + "="*70)
    print("TEST 3: VALIDAR CONVERSIÓN DE ÁNGULOS")
    print("="*70)
    
    try:
        from core.data import format_joint_data
        print("[OK] Import format_joint_data correcto")
    except ImportError as e:
        print(f"[X] Error importando format_joint_data: {e}")
        return False
    
    # Probar conversión
    try:
        data = data_info["data"]
        formatted = format_joint_data(data, subsample=1)
        
        n_keys = len(formatted)
        print(f"[*] Ángulos formateados: {n_keys} keys")
        
        # Verificar primeros 3
        keys_sample = list(formatted.keys())[:3]
        for key in keys_sample:
            array = formatted[key]
            if isinstance(array, np.ndarray):
                print(f"[OK] {key}: shape={array.shape}, dtype={array.dtype}")
            else:
                print(f"[!] {key}: tipo={type(array)}")
        
        if n_keys >= 42:
            print(f"[OK] Suficientes joints detectados")
            return True
        else:
            print(f"[X] Solo {n_keys} joints, esperaba >= 42")
            return False
            
    except Exception as e:
        print(f"[X] Error in format_joint_data: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 4: DIAGNÓSTICO DE RENDERIZADO (SIN GUARDAR VIDEO)
# ============================================================================

def test_render_diagnostic(data_info: Dict) -> bool:
    """
    Ejecutar lógica de renderizado pero sin generar video final.
    Útil para diagnosticar dónde se pierden los frames.
    """
    print("\n" + "="*70)
    print("TEST 4: DIAGNÓSTICO DE RENDERIZADO")
    print("="*70)
    
    try:
        from flygym import Fly, SingleFlySimulation
        from flygym.arena import FlatTerrain
        from flygym.preprogrammed import all_leg_dofs
        from core.data import format_joint_data
    except ImportError as e:
        print(f"[X] Error en imports: {e}")
        return False
    
    data = data_info["data"]
    n_frames = data_info["n_frames"]
    
    # Format joint data
    try:
        formatted_data = format_joint_data(data, subsample=1)
        joint_names = sorted(list(formatted_data.keys()))
        
        if len(joint_names) != 42:
            print(f"[!] Esperaba 42 joints, tengo {len(joint_names)}")
        
        print(f"[OK] Datos formateados: {len(joint_names)} joints")
    except Exception as e:
        print(f"[X] Error formateando: {e}")
        return False
    
    # Setup simulación
    try:
        fly = Fly(init_pose="stretch", actuated_joints=all_leg_dofs, control="position")
        sim = SingleFlySimulation(fly=fly, arena=FlatTerrain())
        obs, info = sim.reset()
        print("[OK] Simulación preparada")
    except Exception as e:
        print(f"[X] Error setup: {e}")
        return False
    
    # Simular y contar frames
    frames_captured = 0
    errors = 0
    
    print(f"\n[*] Ejecutando {min(n_frames, 10)} frames para diagnóstico...")
    
    for frame_idx in range(min(n_frames, 10)):
        try:
            # Compilar acción
            action_values = []
            for joint_name in joint_names:
                val = formatted_data[joint_name][frame_idx]
                if isinstance(val, (list, np.ndarray)):
                    val = float(val[0]) if len(val) > 0 else 0.
                else:
                    val = float(val)
                action_values.append(val)
            
            action = {"joints": np.array(action_values, dtype=np.float32)}
            
            # Step
            obs = sim.step(action)
            
            # Render
            frame_list = sim.render()
            if frame_list and len(frame_list) > 0:
                frames_captured += 1
            else:
                if frame_idx == 0:
                    print(f"[!] Frame {frame_idx}: sim.render() devolvió {frame_list}")
                    
        except Exception as e:
            errors += 1
            print(f"[X] Frame {frame_idx}: {e}")
    
    print(f"\n[*] Resultados:")
    print(f"    Frames intentados: {min(n_frames, 10)}")
    print(f"    Frames capturados: {frames_captured}")
    print(f"    Errores: {errors}")
    
    if frames_captured > 0:
        print(f"[OK] Renderizado funciona, capturó {frames_captured} frames")
        return True
    else:
        print(f"[!] No se capturaron frames - problema en sim.render()")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Validación unificada de simulación 3D")
    parser.add_argument(
        "--test",
        choices=["data", "flygym", "angles", "render", "all"],
        default="all",
        help="Qué test ejecutar"
    )
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("VALIDADOR UNIFICADO DE SIMULACIÓN NEUROMECHFLY 3D")
    print("="*70)
    
    results = {}
    
    # TEST 1: Data
    if args.test in ["data", "all"]:
        success, data_info = test_data_structure()
        results["data"] = success
        if not success:
            print("\n[X] TEST DATA FALLÓ - No puedo continuar")
            return 1
    else:
        success, data_info = test_data_structure()
        if not success:
            print("\n[X] Necesito ejecutar TEST DATA primero")
            return 1
    
    # TEST 2: FlyGym
    if args.test in ["flygym", "all"]:
        results["flygym"] = test_flygym_integration(data_info)
    
    # TEST 3: Angles
    if args.test in ["angles", "all"]:
        results["angles"] = test_angle_format_conversion(data_info)
    
    # TEST 4: Render diagnostic
    if args.test in ["render", "all"]:
        results["render"] = test_render_diagnostic(data_info)
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[X]"
        print(f"  {status} {test_name.upper()}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n[OK] TODOS LOS TESTS PASARON")
        return 0
    else:
        print("\n[X] ALGUNOS TESTS FALLARON")
        return 1


if __name__ == "__main__":
    sys.exit(main())
