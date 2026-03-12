#!/usr/bin/env python3
"""
Script de validación rápida de arquitectura modular.

Verifica que todos los módulos pueden importarse correctamente.
Útil para debugging y verificación post-implementación.

Uso:
    python tools/validate_modular_architecture.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def validate_imports():
    """Validar que todos los módulos pueden importarse."""
    
    print(f"\n{'='*70}")
    print("VALIDACION DE ARQUITECTURA MODULAR")
    print(f"{'='*70}\n")
    
    tests = []
    
    # Test 1: SimulationRunner
    print("[1/5] Validando SimulationRunner...", end=" ")
    try:
        from workflow.simulation_runner import SimulationRunner
        runner_instance = SimulationRunner(verbose=False)
        print("[OK]")
        tests.append(("SimulationRunner", True))
    except Exception as e:
        print(f"[FAIL] {e}")
        tests.append(("SimulationRunner", False))
    
    # Test 2: SimulationValidator
    print("[2/5] Validando SimulationValidator...", end=" ")
    try:
        from workflow.simulation_validator import SimulationValidator
        # No se instancia sin CSV, pero se puede importar
        print("[OK]")
        tests.append(("SimulationValidator", True))
    except Exception as e:
        print(f"[FAIL] {e}")
        tests.append(("SimulationValidator", False))
    
    # Test 3: MuJoCoRenderer
    print("[3/5] Validando MuJoCoRenderer...", end=" ")
    try:
        from rendering.mujoco_renderer import MuJoCoRenderer
        # No se instancia sin datos, pero se puede importar
        print("[OK]")
        tests.append(("MuJoCoRenderer", True))
    except Exception as e:
        print(f"[FAIL] {e}")
        tests.append(("MuJoCoRenderer", False))
    
    # Test 4: SimulationWorkflow
    print("[4/5] Validando SimulationWorkflow...", end=" ")
    try:
        from workflow.simulation_workflow import SimulationWorkflow
        workflow_instance = SimulationWorkflow(verbose=False)
        print("[OK]")
        tests.append(("SimulationWorkflow", True))
    except Exception as e:
        print(f"[FAIL] {e}")
        tests.append(("SimulationWorkflow", False))
    
    
    # Test 5: Core modules
    print("[5/5] Validando módulos core (src)...", end=" ")
    try:
        from olfaction.odor_field import OdorField
        from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
        print("[OK]")
        tests.append(("Core modules", True))
    except Exception as e:
        print(f"[FAIL] {e}")
        tests.append(("Core modules", False))
    
    # Summary
    print(f"\n{'='*70}")
    print("RESUMEN")
    print(f"{'='*70}\n")
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"Pruebas pasadas: {passed}/{total}")
    print()
    
    for name, result in tests:
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print()
    
    if passed == total:
        print("[SUCCESS] TODAS LAS VALIDACIONES PASARON")
        print("\nLa arquitectura modular esta lista para usar:")
        print(f"  python tools/run_complete_3d_simulation.py --help")
        return 0
    else:
        print(f"[ERROR] {total - passed} VALIDACION(ES) FALLARON")
        print("\nVerifica los errores arriba y asegúrate de:")
        print("  - Tener FlyGym instalado (opcional pero recomendado)")
        print("  - Tener PyOpenGL instalado para detección GPU")
        return 1


if __name__ == "__main__":
    exit_code = validate_imports()
    sys.exit(exit_code)
