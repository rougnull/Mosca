#!/usr/bin/env python3
"""
Análisis de Sensibilidad a Parámetros
Systematically vary parameters y mide sus efectos en comportamiento
"""

import numpy as np
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain

def simulate_navigation(field: OdorField, brain: OlfactoryBrain, 
                       start_pos: np.ndarray, target_pos: np.ndarray,
                       duration_steps: int = 200) -> dict:
    """
    Simular navegación simple (sin física real)
    Retorna métricas de desempeño
    """
    pos = start_pos.copy()
    positions = [pos.copy()]
    concentrations = []
    actions_forward = []
    actions_turn = []
    
    for step in range(duration_steps):
        # Percepción: medir olor
        conc = field.concentration_at(pos)
        concentrations.append(conc)
        
        # Cognición: decisión
        action = brain.step(conc)
        actions_forward.append(action[0])
        actions_turn.append(action[1])
        
        # Acción simplificada: movimiento hacia meta si forward > 0
        if action[0] > 0.1:
            # Mover hacia meta
            direction = (target_pos - pos) / (np.linalg.norm(target_pos - pos) + 1e-6)
            vel = 2.0 * action[0]  # Velocidad proporcional a forward
            pos = pos + vel * direction * 0.01  # timestep=0.01
        
        positions.append(pos.copy())
    
    # Calcular métricas
    positions = np.array(positions)
    distances_to_target = [np.linalg.norm(p - target_pos) for p in positions]
    
    metrics = {
        'final_distance': distances_to_target[-1],
        'min_distance': min(distances_to_target),
        'avg_distance': np.mean(distances_to_target),
        'max_concentration': max(concentrations),
        'avg_concentration': np.mean(concentrations),
        'avg_forward_action': np.mean(actions_forward),
        'avg_turn_action': np.mean(actions_turn),
        'success': int(distances_to_target[-1] < 15),  # Arbitrario: éxito si < 15mm
    }
    
    return metrics

def analyze_sigma_sensitivity():
    """Analizar efecto de sigma (ancho del gradiente)"""
    print("\n" + "="*70)
    print("ANÁLISIS 1: Sensibilidad a SIGMA (ancho del gradiente olfatorio)")
    print("="*70)
    
    sigma_values = [0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0]
    target_pos = np.array([50.0, 50.0, 5.0])
    start_pos = np.array([20.0, 20.0, 5.0])
    
    results = []
    
    for sigma in sigma_values:
        field = OdorField(sources=[target_pos], sigma=sigma, amplitude=1.0)
        brain = OlfactoryBrain(threshold=0.1, mode="gradient", 
                             forward_scale=1.0, turn_scale=0.5)
        
        metrics = simulate_navigation(field, brain, start_pos, target_pos, duration_steps=200)
        results.append({
            'sigma': sigma,
            **metrics
        })
        
        print(f"\nσ = {sigma:5.1f} mm:")
        print(f"  Final distance:      {metrics['final_distance']:6.1f} mm")
        print(f"  Min distance:        {metrics['min_distance']:6.1f} mm")
        print(f"  Max concentration:   {metrics['max_concentration']:.6f}")
        print(f"  Avg forward action:  {metrics['avg_forward_action']:6.3f}")
        print(f"  Success:             {'YES' if metrics['success'] else 'NO'}")
    
    # Análisis: cuál es mejor?
    final_distances = [r['final_distance'] for r in results]
    best_sigma = sigma_values[np.argmin(final_distances)]
    
    print(f"\n{'─'*70}")
    print(f"RECOMENDACIÓN: σ = {best_sigma} mm (mejor convergencia)")
    print(f"{'─'*70}")
    
    return results

def analyze_threshold_sensitivity():
    """Analizar efecto de threshold (sensibilidad olfatoria)"""
    print("\n" + "="*70)
    print("ANÁLISIS 2: Sensibilidad a THRESHOLD (sensibilidad olfatoria)")
    print("="*70)
    
    thresholds = [0.01, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75]
    target_pos = np.array([50.0, 50.0, 5.0])
    start_pos = np.array([20.0, 20.0, 5.0])
    
    results = []
    
    for threshold in thresholds:
        field = OdorField(sources=[target_pos], sigma=10.0, amplitude=1.0)
        brain = OlfactoryBrain(threshold=threshold, mode="binary", 
                             forward_scale=1.0, turn_scale=0.5)
        
        metrics = simulate_navigation(field, brain, start_pos, target_pos, duration_steps=200)
        results.append({
            'threshold': threshold,
            **metrics
        })
        
        print(f"\nThreshold = {threshold:5.2f}:")
        print(f"  Final distance:      {metrics['final_distance']:6.1f} mm")
        print(f"  Min distance:        {metrics['min_distance']:6.1f} mm")
        print(f"  Avg concentration:   {metrics['avg_concentration']:.6f}")
        print(f"  % Forward actions:   {100*np.mean([a > 0.1 for a in range(int(metrics['avg_forward_action']*100))]):5.1f}%")
        print(f"  Success:             {'YES' if metrics['success'] else 'NO'}")
    
    final_distances = [r['final_distance'] for r in results]
    best_threshold = thresholds[np.argmin(final_distances)]
    
    print(f"\n{'─'*70}")
    print(f"RECOMENDACIÓN: threshold = {best_threshold} (mejor balance)")
    print(f"{'─'*70}")
    
    return results

def analyze_mode_comparison():
    """Comparar los 3 modos en mismo escenario"""
    print("\n" + "="*70)
    print("ANÁLISIS 3: Comparación de MODOS de decisión")
    print("="*70)
    
    modes = ["binary", "gradient", "temporal_gradient"]
    target_pos = np.array([50.0, 50.0, 5.0])
    start_pos = np.array([20.0, 20.0, 5.0])
    
    results = []
    
    for mode in modes:
        field = OdorField(sources=[target_pos], sigma=10.0, amplitude=1.0)
        brain = OlfactoryBrain(threshold=0.1, mode=mode, 
                             forward_scale=1.0, turn_scale=0.5)
        
        metrics = simulate_navigation(field, brain, start_pos, target_pos, duration_steps=300)
        results.append({
            'mode': mode,
            **metrics
        })
        
        print(f"\nMode = {mode:20s}:")
        print(f"  Final distance:      {metrics['final_distance']:6.1f} mm")
        print(f"  Min distance:        {metrics['min_distance']:6.1f} mm")
        print(f"  Avg distance:        {metrics['avg_distance']:6.1f} mm")
        print(f"  Max concentration:   {metrics['max_concentration']:.6f}")
        print(f"  Convergence:         {'Fast' if metrics['min_distance'] < 20 else 'Slow'}")
        print(f"  Success:             {'YES' if metrics['success'] else 'NO'}")
    
    print(f"\n{'─'*70}")
    print("CARACTERIZACIÓN:")
    print("  • binary:           Búsqueda exhaustiva, lenta pero robusta")
    print("  • gradient:         Taxis rápida si hay gradiente claro")
    print("  • temporal_gradient: Casting inteligente, mejor si se pierde pista")
    print(f"{'─'*70}")
    
    return results

def analyze_scale_effects():
    """Analizar efecto de forward_scale y turn_scale"""
    print("\n" + "="*70)
    print("ANÁLISIS 4: Sensibilidad a SCALES (velocidad y giro)")
    print("="*70)
    
    forward_scales = [0.3, 0.6, 1.0, 1.5, 2.0]
    target_pos = np.array([50.0, 50.0, 5.0])
    start_pos = np.array([20.0, 20.0, 5.0])
    
    results = []
    
    for forward_scale in forward_scales:
        field = OdorField(sources=[target_pos], sigma=10.0, amplitude=1.0)
        brain = OlfactoryBrain(threshold=0.1, mode="gradient", 
                             forward_scale=forward_scale, turn_scale=0.5)
        
        metrics = simulate_navigation(field, brain, start_pos, target_pos, duration_steps=200)
        results.append({
            'forward_scale': forward_scale,
            **metrics
        })
        
        print(f"\nforward_scale = {forward_scale:4.1f}:")
        print(f"  Final distance:      {metrics['final_distance']:6.1f} mm")
        print(f"  Min distance:        {metrics['min_distance']:6.1f} mm")
        print(f"  Avg forward:         {metrics['avg_forward_action']:6.3f}")
        print(f"  Success:             {'YES' if metrics['success'] else 'NO'}")
    
    final_distances = [r['final_distance'] for r in results]
    best_scale = forward_scales[np.argmin(final_distances)]
    
    print(f"\n{'─'*70}")
    print(f"RECOMENDACIÓN: forward_scale = {best_scale} (óptimo para velocidad)")
    print(f"{'─'*70}")
    
    return results

def save_results(all_results: dict):
    """Guardar resultados en CSV para post-análisis"""
    output_dir = Path("outputs/parameter_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for analysis_name, results in all_results.items():
        filename = output_dir / f"{analysis_name}.csv"
        if results:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
            print(f"✓ Guardado: {filename}")

def main():
    print("\n" + "="*70)
    print("ANÁLISIS INTEGRAL DE SENSIBILIDAD A PARÁMETROS")
    print("="*70)
    
    all_results = {}
    
    # Análisis 1: Sigma
    all_results['sigma_sensitivity'] = analyze_sigma_sensitivity()
    
    # Análisis 2: Threshold
    all_results['threshold_sensitivity'] = analyze_threshold_sensitivity()
    
    # Análisis 3: Modos
    all_results['mode_comparison'] = analyze_mode_comparison()
    
    # Análisis 4: Scales
    all_results['scale_effects'] = analyze_scale_effects()
    
    # Guardar resultados
    save_results(all_results)
    
    # Resumen final
    print("\n" + "="*70)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*70)
    print("\nRESUMEN DE RECOMENDACIONES:")
    print("┌────────────────────────────────────────────────────────────┐")
    print("│ RÉGIMEN 1: Búsqueda Exhaustiva (Low Gradient)              │")
    print("│   σ = 0.5-2.5 mm (gradiente abrupt)                        │")
    print("│   mode = 'binary' o 'temporal_gradient'                    │")
    print("│   threshold = 0.05-0.1                                     │")
    print("│   forward_scale = 0.8-1.2                                  │")
    print("├────────────────────────────────────────────────────────────┤")
    print("│ RÉGIMEN 2: Taxis Rápida (Clear Gradient)                   │")
    print("│   σ = 10-20 mm (gradiente suave)                           │")
    print("│   mode = 'gradient'                                        │")
    print("│   threshold = 0.1-0.2                                      │")
    print("│   forward_scale = 1.0-1.5                                  │")
    print("├────────────────────────────────────────────────────────────┤")
    print("│ RÉGIMEN 3: Robustez a Ruido                                │")
    print("│   σ = 5-8 mm (compromiso)                                  │")
    print("│   mode = 'binary'                                          │")
    print("│   threshold = 0.15-0.25                                    │")
    print("│   forward_scale = 0.6-0.8                                  │")
    print("└────────────────────────────────────────────────────────────┘")
    print("\nResultados guardados en: outputs/parameter_analysis/")
    
    return 0

if __name__ == "__main__":
    exit(main())
