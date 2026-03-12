"""
Script de diagnóstico crítico: Identificar el problema con la recepción de olor.

Este script ejecuta una simulación breve con logging extremadamente detallado
de CADA paso para identificar exactamente dónde se pierde la señal de olor.

Registra:
- Posición de la mosca (x, y, z)
- Distancia a fuente de olor
- Concentración de olor detectada
- Salida del cerebro olfatorio
- Acción motora resultante
- Velocidad y movimiento de la mosca
"""

import sys
from pathlib import Path
import numpy as np
import json
from datetime import datetime
import csv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.olfaction.odor_field import OdorField
from src.controllers.olfactory_brain import OlfactoryBrain
from src.controllers.brain_fly import BrainFly
from src.simulation.olfactory_sim import OlfactorySimulation

def debug_odor_reception():
    """Ejecutar test de diagnóstico de recepción de olor."""
    
    # ============================================================================
    # PARTE 1: Verificar que el campo de olor funciona correctamente
    # ============================================================================
    print("\n" + "="*80)
    print("DIAGNÓSTICO 1: Verificar campo de olor")
    print("="*80)
    
    # Crear campo de olor simple
    odor_source = (50, 50, 5)  # Centro de la arena
    odor_field = OdorField(
        sources=odor_source,
        sigma=5.0,  # Muy gradual
        amplitude=1.0  # Máximo: 1.0
    )
    
    print(f"✓ Campo de olor creado")
    print(f"  - Fuente: {odor_source}")
    print(f"  - Sigma (dispersión): 5.0 mm")
    print(f"  - Amplitud máxima: 1.0")
    
    # Probar concentración en varios puntos
    test_points = [
        ("En la fuente", np.array(odor_source)),
        ("1mm de la fuente", np.array(odor_source) + np.array([1, 0, 0])),
        ("5mm de la fuente", np.array(odor_source) + np.array([5, 0, 0])),
        ("10mm de la fuente", np.array(odor_source) + np.array([10, 0, 0])),
        ("20mm de la fuente", np.array(odor_source) + np.array([20, 0, 0])),
        ("En esquina arena (10,10,5)", np.array([10, 10, 5])),
        ("Posición inicial mosca (10,10,2)", np.array([10, 10, 2])),
    ]
    
    print("\nConcentración en puntos de prueba:")
    for label, pos in test_points:
        conc = odor_field.concentration_at(pos)
        dist = np.linalg.norm(pos - np.array(odor_source))
        print(f"  {label:30} | conc={conc:.6f} | dist={dist:.2f}mm")
    
    # ============================================================================
    # PARTE 2: Verificar que el cerebro olfatorio funciona correctamente
    # ============================================================================
    print("\n" + "="*80)
    print("DIAGNÓSTICO 2: Verificar cerebro olfatorio")
    print("="*80)
    
    for mode in ["binary", "gradient", "temporal_gradient"]:
        print(f"\nModo: {mode}")
        brain = OlfactoryBrain(threshold=0.01, mode=mode, forward_scale=1.0, turn_scale=0.5)
        
        test_concentrations = [0.0, 0.05, 0.1, 0.2, 0.5, 0.8, 1.0]
        print(f"  Concentración → Salida [forward, turn]")
        
        for conc in test_concentrations:
            output = brain.step(conc)
            print(f"    {conc:.2f}           → [forward={output[0]:+.2f}, turn={output[1]:+.2f}]")
    
    # ============================================================================
    # PARTE 3: Simulación breve con logging detallado
    # ============================================================================
    print("\n" + "="*80)
    print("DIAGNÓSTICO 3: Simulación con logging detallado")
    print("="*80)
    
    # Crear componentes
    odor_field = OdorField(sources=odor_source, sigma=5.0, amplitude=1.0)
    brain = OlfactoryBrain(threshold=0.01, mode="gradient", forward_scale=1.0, turn_scale=0.5)
    
    # Nota: BrainFly requiere FlyGym, simularemos el comportamiento sin simulación completa
    print("\n⚠ Nota: Usando simulación teórica (sin FlyGym real)")
    print("  Los datos mostrados son predichos basados en la lógica del código")
    
    # Simular trayectoria teórica de la mosca
    dt = 0.01  # 10ms control timestep
    duration = 5.0  # 5 segundos
    steps = int(duration / dt)
    
    # Posición inicial (esquina opuesta a la fuente)
    position = np.array([10.0, 10.0, 2.0])
    velocity = np.array([0.0, 0.0, 0.0])  # Velocidad de locomoción
    
    # Logging
    log_data = []
    
    print(f"\nSimulando {steps} pasos ({duration}s) con dt={dt}s")
    print("Posición inicial:", position)
    print("Fuente de olor:", odor_source)
    print(f"\nTime(s) | Pos_X(mm) | Pos_Y(mm) | Conc  | Brain_Fw | Brain_Turn | Vel(mm/s)")
    print("-" * 90)
    
    brain.reset()
    
    for step_idx in range(steps):
        t = step_idx * dt
        
        # Leer olor en posición actual
        odor_conc = odor_field.concentration_at(position)
        
        # Cerebro procesa olor
        motor_signal = brain.step(odor_conc)  # [forward, turn]
        
        # Simular movimiento muy simple:
        # forward = velocidad hacia adelante
        # turn = cambio de dirección
        forward_speed = motor_signal[0] * 5.0  # mm/s (escalar para visualizar)
        
        # Dirección hacia la fuente (para ver si el movimiento es correcto)
        vec_to_source = odor_source - position
        dist_to_source = np.linalg.norm(vec_to_source)
        
        if dist_to_source > 0.1:
            direction = vec_to_source / dist_to_source
        else:
            direction = np.array([0, 0, 0])
        
        # Actualizar posición (simulación simplista)
        # Aquí es donde deberíamos ver si el motor causaría movimiento
        position = position + direction * forward_speed * dt
        
        # Distancia a fuente
        dist = np.linalg.norm(position - np.array(odor_source))
        
        if step_idx % 10 == 0:  # Log cada 100ms
            print(f"{t:7.2f} | {position[0]:9.2f} | {position[1]:9.2f} | "
                  f"{odor_conc:5.3f} | {motor_signal[0]:+8.2f} | {motor_signal[1]:+10.2f} | "
                  f"{forward_speed:7.2f}")
        
        log_data.append({
            "time": t,
            "pos_x": position[0],
            "pos_y": position[1],
            "pos_z": position[2],
            "dist_to_source": dist,
            "odor_concentration": float(odor_conc),
            "brain_forward": float(motor_signal[0]),
            "brain_turn": float(motor_signal[1]),
            "velocity": float(forward_speed)
        })
    
    # ============================================================================
    # PARTE 4: Guardar log detallado
    # ============================================================================
    print("\n" + "="*80)
    print("DIAGNÓSTICO 4: Guardando resultados")
    print("="*80)
    
    output_dir = Path("outputs/debug_odor")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Guardar como CSV
    csv_path = output_dir / "odor_debug_log.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "time", "pos_x", "pos_y", "pos_z", "dist_to_source",
            "odor_concentration", "brain_forward", "brain_turn", "velocity"
        ])
        writer.writeheader()
        writer.writerows(log_data)
    
    print(f"✓ Log guardado: {csv_path}")
    
    # Guardar análisis
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "odor_source": list(odor_source),
            "odor_sigma": 5.0,
            "brain_mode": "gradient",
            "brain_threshold": 0.01,
            "sim_duration": duration,
            "dt": dt
        },
        "results": {
            "max_odor_concentration": float(max([d["odor_concentration"] for d in log_data])),
            "final_distance_to_source": float(log_data[-1]["dist_to_source"]),
            "initial_distance": float((np.linalg.norm(np.array([10, 10, 2]) - np.array(odor_source)))),
            "distance_reduction": float((np.linalg.norm(np.array([10, 10, 2]) - np.array(odor_source))) - log_data[-1]["dist_to_source"]),
            "total_forward_signal": float(sum([d["brain_forward"] for d in log_data])),
            "avg_brain_forward": float(np.mean([d["brain_forward"] for d in log_data])),
        }
    }
    
    analysis_path = output_dir / "debug_analysis.json"
    with open(analysis_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"✓ Análisis guardado: {analysis_path}")
    
    # ============================================================================
    # PARTE 5: Diagnóstico final
    # ============================================================================
    print("\n" + "="*80)
    print("DIAGNÓSTICO FINAL")
    print("="*80)
    
    r = analysis["results"]
    print(f"\n✓ Concentración DETECTADA: {r['max_odor_concentration']:.4f}")
    
    if r['max_odor_concentration'] < 0.001:
        print("  ⚠ PROBLEMA 1: El olor es MUY DÉBIL")
        print("    → Solución: Reducir sigma (difusión) u aumentar amplitude")
    else:
        print("  ✓ El olor sí se detecta correctamente")
    
    print(f"\n✓ Cerebro ACTIVADO: {r['avg_brain_forward']:.4f} (promedio)")
    
    if abs(r['avg_brain_forward']) < 0.01:
        print("  ⚠ PROBLEMA 2: El cerebro NO RESPONDE al olor")
        print("    → El cerebro recibe olor pero no genera acción")
        print("    → Verificar: umbral, escala, o lógica del modo")
    else:
        print("  ✓ El cerebro sí genera señal forward")
    
    print(f"\n✓ Movimiento RESULTANTE: {r['distance_reduction']:.2f} mm más cerca")
    
    if r['distance_reduction'] < 0.1:
        print("  ⚠ PROBLEMA 3: La mosca NO SE MUEVE hacia el olor")
        print("    → El motor NOT está siendo aplicado correctamente")
        print("    → Verificar: integración BrainFly-FlyGym")
    else:
        print("  ✓ La mosca se mueve hacia el olor")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    debug_odor_reception()
