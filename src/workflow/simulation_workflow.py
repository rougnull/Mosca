#!/usr/bin/env python3
"""
Orquestador de workflow de simulación.

Ejecuta el pipeline completo en orden:
1. RUNNER: Ejecuta simulación, guarda datos crudos
2. VALIDATOR: Verifica que simulación fue exitosa
3. RENDERER: Si es exitosa, renderiza 3D
4. REPORT: Genera reporte final

Uso:
    from tools.simulation.simulation_workflow import SimulationWorkflow
    
    workflow = SimulationWorkflow(output_dir="outputs/simulations")
    workflow.run(
        odor_field=field,
        brain=brain,
        duration=10,
        render_if_successful=True,
    )
"""

import sys
from pathlib import Path
import json
from typing import Tuple, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from .simulation_runner import SimulationRunner
from .simulation_validator import SimulationValidator


class SimulationWorkflow:
    """
    Orquesta el flujo completo: simulación → validación → renderizado.
    
    Características:
    - Separación clara de responsabilidades
    - Detiene en validación si falla (no renderiza datos malos)
    - Genera reporte final con logs
    - Modular: cada paso puede ejecutarse independientemente
    """
    
    def __init__(
        self,
        output_dir: str = "outputs/simulations",
        sim_type: str = "kinematic",
        verbose: bool = True
    ):
        """
        Inicializar workflow.
        
        Args:
            output_dir: Directorio base para outputs
            sim_type: "kinematic" o "mujoco"
            verbose: Imprimir progreso
        """
        self.output_dir = output_dir
        self.sim_type = sim_type
        self.verbose = verbose
        
        # Componentes del pipeline
        self.runner = SimulationRunner(output_dir, sim_type, verbose)
        
        # Estado
        self.current_sim_dir = None
        self.validation_success = False
        self.workflow_report = {}
    
    def run(
        self,
        odor_field,
        brain,
        duration: float = 10.0,
        arena_size: Tuple[float, float, float] = (100, 100, 10),
        source_pos: Tuple[float, float, float] = (50, 50, 5),
        dt: float = 0.01,
        render_on_success: bool = True,
        run_validator: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ejecutar pipeline completo: RUNNER → VALIDATOR → RENDERER.
        
        Args:
            odor_field: OdorField instance
            brain: OlfactoryBrain instance
            duration: Duración simulación (segundos)
            arena_size: Tamaño arena (x, y, z)
            source_pos: Posición fuente (x, y, z)
            dt: Timestep control
            render_on_success: Renderizar 3D solo si validación es exitosa
            run_validator: Ejecutar validación (default=True)
            **kwargs: Args adicionales
        
        Returns:
            Dict con resultado total del workflow
        """
        
        print(f"\n{'='*70}")
        print("SIMULATION WORKFLOW - PIPELINE COMPLETO")
        print(f"{'='*70}\n")
        
        # PASO 1: RUNNER
        print("📋 PASO 1: EJECUTANDO SIMULACIÓN...")
        print("-" * 70)
        
        try:
            self.current_sim_dir = self.runner.run(
                odor_field=odor_field,
                brain=brain,
                duration=duration,
                arena_size=arena_size,
                source_pos=source_pos,
                dt=dt,
                **kwargs
            )
        except Exception as e:
            self.workflow_report = {
                "status": "FAILED",
                "step": "RUNNER",
                "error": str(e),
            }
            
            if self.verbose:
                print(f"\n✗ Simulación falló: {e}")
            
            return self.workflow_report
        
        # PASO 2: VALIDATOR
        if run_validator:
            print("\n📋 PASO 2: VALIDANDO SIMULACIÓN...")
            print("-" * 70)
            
            try:
                validator = SimulationValidator(
                    self.current_sim_dir / "trajectory.csv",
                    self.current_sim_dir / "config.json",
                    verbose=self.verbose
                )
                
                success, val_results = validator.validate()
                self.validation_success = success
                
                # Guardar reporte de validación
                validator.save_validation_report(self.current_sim_dir / "validation.json")
                
            except Exception as e:
                self.workflow_report = {
                    "status": "FAILED",
                    "step": "VALIDATOR",
                    "error": str(e),
                }
                
                if self.verbose:
                    print(f"\n✗ Validación falló: {e}")
                
                return self.workflow_report
        else:
            # Si no se ejecuta validador, asumir que fue exitosa
            self.validation_success = True
            success = True
            val_results = {"skipped": True}
        
        # PASO 3: RENDERER (solo si validación fue exitosa)
        if render_on_success and self.validation_success:
            print("\n📋 PASO 3: RENDERIZANDO 3D (Simulación exitosa)...")
            print("-" * 70)
            
            try:
                self._render_3d(self.current_sim_dir)
            except Exception as e:
                if self.verbose:
                    print(f"\n⚠ Renderizado 3D falló (continuando): {e}")
                # El renderizado es opcional
        
        elif render_on_success and not self.validation_success:
            if self.verbose:
                print("\n⏭ SALTANDO PASO 3: Renderizado deshabilitado (validación falló)")
                print("   Para renderizar datos fallidos, ejecute manualmente:")
                print(f"   python tools/3d_renderer.py {self.current_sim_dir}")
        
        # REPORTE FINAL
        self.workflow_report = {
            "status": "SUCCESS" if self.validation_success else "VALIDATION_FAILED",
            "simulation_dir": str(self.current_sim_dir),
            "total_timesteps": len(self.runner.times),
            "duration": duration,
            "validation": {
                "executed": run_validator,
                "success": self.validation_success,
                "results": val_results,
            },
            "rendering": {
                "executed": render_on_success and self.validation_success,
                "condition": "validation_success",
            }
        }
        
        self._print_final_report()
        
        return self.workflow_report
    
    def _render_3d(self, sim_dir: Path):
        """
        Renderizar 3D usando el módulo 3d_renderer.
        
        Este es un placeholder - el rendering real se implementa en 3d_renderer.py
        """
        # Aquí se llamaría al módulo 3d_renderer cuando esté listo
        # Por ahora, solo log
        
        if self.verbose:
            print(f"  [PREPARACIÓN] Renderizado 3D configurado para {sim_dir}")
            print(f"  Nota: Module 3d_renderer.py manejará rendering GPU-optimizado")
    
    def _print_final_report(self):
        """Imprimir reporte final del workflow."""
        
        print(f"\n{'='*70}")
        print("REPORTE FINAL DEL WORKFLOW")
        print(f"{'='*70}\n")
        
        status = self.workflow_report.get("status", "UNKNOWN")
        status_icon = "✓" if status == "SUCCESS" else "✗" if status == "FAILED" else "⚠"
        
        print(f"{status_icon} Estado: {status}")
        print(f"   Directorio: {self.workflow_report.get('simulation_dir', 'N/A')}")
        print(f"   Timesteps: {self.workflow_report.get('total_timesteps', 'N/A')}")
        print(f"   Duración: {self.workflow_report.get('duration', 'N/A')} s\n")
        
        # Validación
        val_info = self.workflow_report.get("validation", {})
        if val_info.get("executed"):
            val_status = "✓ EXITOSA" if val_info.get("success") else "✗ FALLIDA"
            print(f"Validación: {val_status}")
        
        # Rendering
        rend_info = self.workflow_report.get("rendering", {})
        if rend_info.get("executed"):
            print(f"Renderizado 3D: ✓ EJECUTADO")
        elif status == "SUCCESS":
            print(f"Renderizado 3D: ⏭ SALTADO (no solicitado)")
        else:
            print(f"Renderizado 3D: ⏭ SALTADO (simulación no exitosa)")
        
        print(f"\n{'='*70}\n")
    
    def validate_existing(self, sim_dir: str) -> Dict[str, Any]:
        """
        Validar una simulación existente sin ejecutar de nuevo.
        
        Útil para validar resultados previos.
        
        Args:
            sim_dir: Directorio con trajectory.csv
        
        Returns:
            Resultado de validación
        """
        sim_dir = Path(sim_dir)
        csv_path = sim_dir / "trajectory.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(f"trajectory.csv no encontrado en {sim_dir}")
        
        validator = SimulationValidator(str(csv_path), verbose=self.verbose)
        success, results = validator.validate()
        validator.save_validation_report(sim_dir / "validation.json")
        
        return results


def main():
    """Script de demostración."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Workflow de simulación olfatoria")
    parser.add_argument("--duration", type=float, default=10.0, help="Duración simulación (s)")
    parser.add_argument("--sim-type", choices=["kinematic", "mujoco"], default="kinematic")
    parser.add_argument("--render", action="store_true", help="Renderizar si exitosa")
    parser.add_argument("--output-dir", default="outputs/simulations")
    
    args = parser.parse_args()
    
    # Importar componentes
    from olfaction.odor_field import OdorField
    from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
    
    # Crear instancias
    odor_field = OdorField(
        sources=[(50, 50)],
        sigma=15.0,
        amplitude=1.0
    )
    
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8,
        threshold=0.01,
    )
    
    # Ejecutar workflow
    workflow = SimulationWorkflow(args.output_dir, args.sim_type)
    result = workflow.run(
        odor_field=odor_field,
        brain=brain,
        duration=args.duration,
        render_on_success=args.render,
    )
    
    print("\nWorkflow Report:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
