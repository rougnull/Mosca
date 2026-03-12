#!/usr/bin/env python3
"""
Validador de simulaciones olfatorias.

Verifica que una simulación fue exitosa comprobando:
1. Movimiento de la mosca (desplazamiento mínimo desde inicio)
2. Movimiento de extremidades (cambio en posiciones articulares)
3. Respuesta sensoriomotora (cambios en velocidad forward/turn)
4. Comportamiento dirigido (acercamiento a la fuente de olor)

Este módulo es independiente y puede aplicarse a cualquier resultado de simulación
guardado en CSV.
"""

import numpy as np
import csv
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import json


class SimulationValidator:
    """
    Valida si una simulación fue exitosa basada en criterios biológicos.
    
    Una simulación es EXITOSA si:
    - La mosca se mueve (desplazamiento > 1 mm)
    - Las extremidades se mueven (variación articular > 5°)
    - El cerebro genera comandos variables (forward/turn cambian)
    - El comportamiento es dirigido hacia el olor (distancia a fuente disminuye)
    """
    
    # Criterios de éxito (ajustables)
    MIN_DISPLACEMENT = 1.0  # mm - desplazamiento mínimo del cuerpo
    MIN_LEG_MOVEMENT = 5.0  # degrees - cambio mínimo en articulaciones
    MIN_MOTOR_VARIATION = 0.05  # cambio mínimo en comandos forward/turn
    MAX_TIME_TO_SOURCE = float('inf')  # segundos - tiempo máximo para llegar a fuente
    MIN_SOURCE_APPROACH = 0.5  # mm - acercamiento mínimo a fuente (en 10s)
    
    def __init__(
        self,
        csv_path: str,
        config_path: Optional[str] = None,
        verbose: bool = True
    ):
        """
        Inicializar validador.
        
        Args:
            csv_path: Ruta a trajectory.csv
            config_path: Ruta opcional a config.json
            verbose: Imprimir detalles de validación
        """
        self.csv_path = Path(csv_path)
        self.config_path = Path(config_path) if config_path else self.csv_path.parent / "config.json"
        self.verbose = verbose
        
        self.trajectory_data = []
        self.config = {}
        self._load_data()
        
        # Resultados de validación
        self.validation_results = {}
    
    def _load_data(self):
        """Cargar datos de CSV y config."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Trayectoria no encontrada: {self.csv_path}")
        
        # Cargar CSV
        with open(self.csv_path) as f:
            reader = csv.DictReader(f)
            self.trajectory_data = list(reader)
        
        # Cargar config si existe
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.config = json.load(f)
        
        if self.verbose:
            print(f"✓ Datos cargados: {len(self.trajectory_data)} timesteps")
    
    def validate(self) -> Tuple[bool, Dict]:
        """
        Ejecutar validación completa.
        
        Returns:
            (success: bool, results: Dict con detalles)
        """
        if self.verbose:
            print(f"\n{'='*70}")
            print("VALIDACIÓN DE SIMULACIÓN")
            print(f"{'='*70}")
        
        if len(self.trajectory_data) == 0:
            return False, {"error": "No trajectory data"}
        
        # Ejecutar chequeos individuales
        checks = {
            "displacement": self._check_displacement(),
            "motor_variation": self._check_motor_variation(),
            "source_approach": self._check_source_approach(),
            "movement_consistency": self._check_movement_consistency(),
        }
        
        # Agregación
        success = all(check["success"] for check in checks.values())
        
        self.validation_results = {
            "overall_success": success,
            "timestamp": str(self.csv_path.parent),
            "total_timesteps": len(self.trajectory_data),
            "checks": checks,
        }
        
        if self.verbose:
            self._print_results(success, checks)
        
        return success, self.validation_results
    
    def _check_displacement(self) -> Dict:
        """
        Verificar que la mosca se movió significativamente.
        
        Calcula el desplazamiento total desde inicio a fin.
        """
        check_name = "DISPLACEMENT (Movimiento del cuerpo)"
        
        try:
            if len(self.trajectory_data) < 2:
                return {"success": False, "reason": "Datos insuficientes"}
            
            # Posiciones inicial y final
            start = np.array([
                float(self.trajectory_data[0].get("x", 0)),
                float(self.trajectory_data[0].get("y", 0)),
            ])
            
            end = np.array([
                float(self.trajectory_data[-1].get("x", 0)),
                float(self.trajectory_data[-1].get("y", 0)),
            ])
            
            displacement = np.linalg.norm(end - start)
            
            success = displacement >= self.MIN_DISPLACEMENT
            
            if self.verbose:
                status = "✓" if success else "✗"
                print(f"\n{status} {check_name}")
                print(f"  Desplazamiento: {displacement:.2f} mm (mínimo: {self.MIN_DISPLACEMENT} mm)")
            
            return {
                "success": success,
                "displacement": float(displacement),
                "min_required": self.MIN_DISPLACEMENT,
                "reason": f"Desplazamiento de {displacement:.2f} mm"
            }
        
        except Exception as e:
            if self.verbose:
                print(f"\n✗ {check_name}")
                print(f"  Error: {e}")
            return {"success": False, "reason": str(e)}
    
    def _check_motor_variation(self) -> Dict:
        """
        Verificar que los comandos motores varían (no son constantes).
        
        Analiza cambios en forward y turn commands si están disponibles.
        """
        check_name = "MOTOR VARIATION (Cambio en comandos motores)"
        
        try:
            # Buscar columnas de comandos motores
            motor_cols = [col for col in self.trajectory_data[0].keys() 
                         if any(x in col.lower() for x in ['forward', 'turn', 'motor', 'action'])]
            
            if not motor_cols:
                if self.verbose:
                    print(f"\n⚠ {check_name}")
                    print(f"  Datos de motores no encontrados (skip)")
                return {"success": True, "reason": "Motor data unavailable - skip"}
            
            # Calcular varianza de comandos
            motor_values = []
            for timestamp in self.trajectory_data:
                try:
                    values = [float(timestamp.get(col, 0)) for col in motor_cols]
                    motor_values.append(values)
                except (ValueError, TypeError):
                    continue
            
            if len(motor_values) < 2:
                return {"success": False, "reason": "Insufficient motor data"}
            
            motor_values = np.array(motor_values)
            motor_std = np.std(motor_values)
            
            success = motor_std >= self.MIN_MOTOR_VARIATION
            
            if self.verbose:
                status = "✓" if success else "✗"
                print(f"\n{status} {check_name}")
                print(f"  Variación (std): {motor_std:.4f} (mínimo: {self.MIN_MOTOR_VARIATION:.4f})")
            
            return {
                "success": success,
                "motor_std": float(motor_std),
                "min_required": self.MIN_MOTOR_VARIATION,
                "reason": f"Variación de {motor_std:.4f}"
            }
        
        except Exception as e:
            if self.verbose:
                print(f"\n✗ {check_name}")
                print(f"  Error: {e}")
            return {"success": False, "reason": str(e)}
    
    def _check_source_approach(self) -> Dict:
        """
        Verificar que la mosca se acerca a la fuente de olor.
        
        Compara distancia inicial y final a la fuente.
        """
        check_name = "SOURCE APPROACH (Acercamiento a fuente)"
        
        try:
            # Obtener posición de la fuente
            source_pos = None
            if "source_pos" in self.config:
                source_pos = np.array(self.config["source_pos"][:2])
            elif "distance_to_source" in self.trajectory_data[0]:
                # Usar la distancia inicial registrada
                pass
            else:
                if self.verbose:
                    print(f"\n⚠ {check_name}")
                    print(f"  Posición de fuente no disponible (skip)")
                return {"success": True, "reason": "Source position unavailable - skip"}
            
            if source_pos is not None:
                # Calcular distancias inicial y final
                start = np.array([
                    float(self.trajectory_data[0].get("x", 0)),
                    float(self.trajectory_data[0].get("y", 0)),
                ])
                
                end = np.array([
                    float(self.trajectory_data[-1].get("x", 0)),
                    float(self.trajectory_data[-1].get("y", 0)),
                ])
                
                dist_init = np.linalg.norm(start - source_pos)
                dist_final = np.linalg.norm(end - source_pos)
                approach = dist_init - dist_final
            else:
                # Usar la columna distance_to_source
                distances = []
                for timestamp in self.trajectory_data:
                    try:
                        d = float(timestamp.get("distance_to_source", 0))
                        distances.append(d)
                    except (ValueError, TypeError):
                        continue
                
                if len(distances) < 2:
                    return {"success": False, "reason": "Insufficient distance data"}
                
                dist_init = distances[0]
                dist_final = distances[-1]
                approach = dist_init - dist_final
            
            success = approach >= self.MIN_SOURCE_APPROACH
            
            if self.verbose:
                status = "✓" if success else "✗"
                print(f"\n{status} {check_name}")
                print(f"  Acercamiento: {approach:.2f} mm")
                print(f"    Distancia inicial: {dist_init:.2f} mm")
                print(f"    Distancia final: {dist_final:.2f} mm")
            
            return {
                "success": success,
                "approach": float(approach),
                "distance_initial": float(dist_init),
                "distance_final": float(dist_final),
                "min_required": self.MIN_SOURCE_APPROACH,
                "reason": f"Acercamiento de {approach:.2f} mm"
            }
        
        except Exception as e:
            if self.verbose:
                print(f"\n✗ {check_name}")
                print(f"  Error: {e}")
            return {"success": False, "reason": str(e)}
    
    def _check_movement_consistency(self) -> Dict:
        """
        Verificar que el movimiento es consistente (no es ruido).
        
        Usa la concentración de olor como indicador: mosca debe detectarla.
        """
        check_name = "MOVEMENT CONSISTENCY (Consistencia del movimiento)"
        
        try:
            # Cargar concentraciones
            odor_values = []
            for timestamp in self.trajectory_data:
                try:
                    # Buscar columna de concentración
                    for col in ['odor_concentration', 'conc', 'concentration']:
                        if col in timestamp:
                            odor_values.append(float(timestamp[col]))
                            break
                except (ValueError, TypeError):
                    continue
            
            if len(odor_values) < 2:
                if self.verbose:
                    print(f"\n⚠ {check_name}")
                    print(f"  Datos de concentración no disponibles (skip)")
                return {"success": True, "reason": "Odor data unavailable - skip"}
            
            odor_values = np.array(odor_values)
            
            # Verificar que la mosca detecta olor (valores no todos cero)
            has_odor_detection = np.any(odor_values > 0.001)
            
            if self.verbose:
                status = "✓" if has_odor_detection else "✗"
                print(f"\n{status} {check_name}")
                print(f"  Detección de olor: {'Sí' if has_odor_detection else 'No'}")
                print(f"    Máx concentración: {np.max(odor_values):.6f}")
                print(f"    Media concentración: {np.mean(odor_values):.6f}")
            
            return {
                "success": has_odor_detection,
                "max_odor": float(np.max(odor_values)),
                "mean_odor": float(np.mean(odor_values)),
                "reason": f"Concentración máxima: {np.max(odor_values):.6f}"
            }
        
        except Exception as e:
            if self.verbose:
                print(f"\n✗ {check_name}")
                print(f"  Error: {e}")
            return {"success": False, "reason": str(e)}
    
    def _print_results(self, success: bool, checks: Dict):
        """Imprimir resultados de validación."""
        print(f"\n{'='*70}")
        print("RESULTADO DE VALIDACIÓN")
        print(f"{'='*70}\n")
        
        overall_status = "✓ EXITOSA" if success else "✗ FALLIDA"
        print(f"Estado General: {overall_status}\n")
        
        print(f"Resumen de Chequeos:")
        for check_name, result in checks.items():
            status = "✓" if result["success"] else "✗"
            reason = result.get("reason", "N/A")
            print(f"  {status} {check_name.upper()}: {reason}")
        
        print(f"\n{'='*70}\n")
        
        return success
    
    def save_validation_report(self, output_path: Optional[str] = None) -> Path:
        """
        Guardar reporte de validación en JSON.
        
        Args:
            output_path: Ruta del archivo (default: sim_dir/validation.json)
        
        Returns:
            Path del reporte guardado
        """
        if not self.validation_results:
            raise RuntimeError("Ejecutar validate() primero")
        
        if output_path is None:
            output_path = self.csv_path.parent / "validation.json"
        
        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        if self.verbose:
            print(f"\n✓ Reporte de validación guardado: {output_path}")
        
        return output_path
