"""
Script de ejemplo: Navegación olfatoria offline

Demuestra el uso de los módulos sin requerir FlyGym instalado.
Genera trayectorias de mosca navegando hacia una fuente de olor.
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain


def simulate_navigation(
    odor_source=(50, 50, 5),
    brain_mode="binary",
    threshold=0.1,
    duration_seconds=30,
    save_output=True,
    plot_results=True
):
    """
    Simular navegación olfatoria offline.
    
    Parameters
    ----------
    odor_source : tuple
        Posición (x, y, z) de la fuente de olor en mm
    brain_mode : str
        Modo del cerebro: "binary", "gradient", o "temporal_gradient"
    threshold : float
        Umbral de concentración para activar aproximación
    duration_seconds : float
        Duración de la simulación
    save_output : bool
        Guardar resultados a CSV
    plot_results : bool
        Mostrar gráficas
    
    Returns
    -------
    dict
        Diccionario con resultados de simulación
    """
    
    # Parámetros de simulación
    dt = 0.01  # 10 ms entre decisiones
    num_steps = int(duration_seconds / dt)
    
    max_speed = 10  # mm/s
    max_angular_speed = 90  # deg/s
    
    print(f"\n{'='*60}")
    print(f"Simulación de Navegación Olfatoria")
    print(f"{'='*60}")
    print(f"Modo cerebro: {brain_mode}")
    print(f"Umbral concentración: {threshold}")
    print(f"Duración: {duration_seconds} s ({num_steps} pasos)")
    print(f"Fuente de olor: {odor_source}")
    print(f"{'='*60}\n")
    
    # Crear campo de olor
    odor_field = OdorField(
        sources=odor_source,
        sigma=10.0,
        amplitude=1.0
    )
    
    # Crear cerebro
    brain = OlfactoryBrain(
        threshold=threshold,
        mode=brain_mode,
        forward_scale=1.0,
        turn_scale=0.5
    )
    
    # Inicializar posición (lejos de la fuente)
    position = np.array([10.0, 10.0, 5.0])
    heading = 0.0  # radianes
    
    # Logs
    positions = [position.copy()]
    odor_log = []
    action_log = []
    times = []
    distances = []
    
    # Simulación
    for step_idx in range(num_steps):
        # Leer concentración
        conc = odor_field.concentration_at(position)
        odor_log.append(conc)
        
        # Ejecutar cerebro
        action = brain.step(conc)  # [forward, turn]
        action_log.append(action)
        
        # Actualizar heading
        heading += np.deg2rad(action[1] * max_angular_speed * dt)
        
        # Actualizar posición
        velocity = max_speed * action[0]
        delta_pos = np.array([
            velocity * np.cos(heading) * dt,
            velocity * np.sin(heading) * dt,
            0
        ])
        position = position + delta_pos
        
        # Mantener dentro de arena
        position[0] = np.clip(position[0], 0, 100)
        position[1] = np.clip(position[1], 0, 100)
        
        positions.append(position.copy())
        times.append(step_idx * dt)
        
        # Calcular distancia a fuente
        dist = np.linalg.norm(position[:2] - np.array(odor_source)[:2])
        distances.append(dist)
        
        # Progreso
        if (step_idx + 1) % 1000 == 0:
            print(f"  Step {step_idx + 1}/{num_steps}: "
                  f"odor={conc:.4f}, dist={dist:.1f} mm, pos=({position[0]:.1f}, {position[1]:.1f})")
    
    positions = np.array(positions)
    odor_log = np.array(odor_log)
    action_log = np.array(action_log)
    distances = np.array(distances)
    
    # Calcular métricas
    total_distance = np.sum(np.linalg.norm(np.diff(positions, axis=0), axis=1))
    
    metrics = {
        "positions": positions,
        "odor_log": odor_log,
        "action_log": action_log,
        "times": np.array(times),
        "distances": distances,
        "total_distance": total_distance,
        "initial_distance": distances[0],
        "final_distance": distances[-1],
        "min_distance": np.min(distances),
        "mean_odor": np.mean(odor_log),
        "final_odor": odor_log[-1],
    }
    
    # Imprimir resumen
    print(f"\nResultados:")
    print(f"  Distancia recorrida: {total_distance:.1f} mm")
    print(f"  Distancia inicial a fuente: {distances[0]:.1f} mm")
    print(f"  Distancia final a fuente: {distances[-1]:.1f} mm")
    print(f"  Distancia mínima alcanzada: {np.min(distances):.1f} mm")
    print(f"  Concentración media: {np.mean(odor_log):.4f}")
    print(f"  Concentración final: {odor_log[-1]:.4f}")
    print(f"  Concentración máxima: {np.max(odor_log):.4f}")
    
    # Graficar
    if plot_results:
        _plot_results(metrics, odor_field)
    
    # Guardar
    if save_output:
        _save_results(metrics, brain_mode, threshold)
    
    return metrics


def _plot_results(metrics, odor_field):
    """Graficar resultados de simulación."""
    positions = metrics["positions"]
    odor_log = metrics["odor_log"]
    action_log = metrics["action_log"]
    times = metrics["times"]
    distances = metrics["distances"]
    
    # Crear malla para visualizar campo
    x = np.linspace(0, 100, 100)
    y = np.linspace(0, 100, 100)
    X, Y = np.meshgrid(x, y)
    pos_grid = np.stack([X, Y, np.full_like(X, 5)], axis=-1)
    conc_grid = odor_field.concentration_at(pos_grid.reshape(-1, 3)).reshape(100, 100)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # Panel 1: Trayectoria
    ax = axes[0, 0]
    contour = ax.contourf(X, Y, conc_grid, levels=20, cmap='hot', alpha=0.8)
    ax.plot(positions[:, 0], positions[:, 1], 'c-', linewidth=1.5, alpha=0.7)
    ax.plot(positions[0, 0], positions[0, 1], 'go', markersize=10, label='Inicio')
    ax.plot(positions[-1, 0], positions[-1, 1], 'r*', markersize=15, label='Final')
    ax.plot(50, 50, 'b*', markersize=20, label='Fuente')
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_title('Trayectoria de navegación')
    ax.legend()
    plt.colorbar(contour, ax=ax, label='Concentración')
    
    # Panel 2: Concentración
    ax = axes[0, 1]
    ax.plot(times, odor_log, 'b-', linewidth=1.5)
    ax.fill_between(times, odor_log, alpha=0.3)
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Concentración')
    ax.set_title('Concentración vs Tiempo')
    ax.grid(True, alpha=0.3)
    
    # Panel 3: Comandos motores
    ax = axes[1, 0]
    ax.plot(times, action_log[:, 0], 'b-', label='Forward', linewidth=1.5)
    ax.plot(times, action_log[:, 1], 'r-', label='Turn', linewidth=1.5)
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Comando motor')
    ax.set_title('Comandos motores vs Tiempo')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim([-1.5, 1.5])
    
    # Panel 4: Distancia a fuente
    ax = axes[1, 1]
    ax.plot(times, distances, 'g-', linewidth=1.5)
    ax.fill_between(times, distances, alpha=0.3, color='g')
    ax.set_xlabel('Tiempo (s)')
    ax.set_ylabel('Distancia a fuente (mm)')
    ax.set_title('Distancia a fuente vs Tiempo')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/olfactory_example.png', dpi=100)
    print(f"\n✓ Gráfica guardada: outputs/olfactory_example.png")
    plt.show()


def _save_results(metrics, brain_mode, threshold):
    """Guardar resultados a CSV."""
    import csv
    from pathlib import Path
    
    output_dir = Path("outputs/olfactory")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    positions = metrics["positions"]
    odor_log = metrics["odor_log"]
    times = metrics["times"]
    
    filename = output_dir / f"navigation_{brain_mode}_th{threshold:.2f}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time_s', 'x_mm', 'y_mm', 'z_mm', 'odor_conc'])
        for t, pos, odor in zip(times, positions, odor_log):
            writer.writerow([t, pos[0], pos[1], pos[2], odor])
    
    print(f"✓ Datos guardados: {filename}")


def compare_strategies():
    """Comparar diferentes estrategias de navegación."""
    print("\n" + "="*60)
    print("COMPARACIÓN DE ESTRATEGIAS DE NAVEGACIÓN")
    print("="*60)
    
    strategies = [
        {"mode": "binary", "threshold": 0.05, "label": "Binary (umbral bajo)"},
        {"mode": "binary", "threshold": 0.1, "label": "Binary (umbral medio)"},
        {"mode": "gradient", "threshold": 0.1, "label": "Gradient"},
        {"mode": "temporal_gradient", "threshold": 0.1, "label": "Temporal Gradient"},
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    results_summary = []
    
    for idx, strategy in enumerate(strategies):
        print(f"\n--- {strategy['label']} ---")
        metrics = simulate_navigation(
            brain_mode=strategy["mode"],
            threshold=strategy["threshold"],
            plot_results=False,
            save_output=False
        )
        
        # Graficar en subplot
        ax = axes[idx // 2, idx % 2]
        
        x = np.linspace(0, 100, 100)
        y = np.linspace(0, 100, 100)
        X, Y = np.meshgrid(x, y)
        odor = OdorField(sources=(50, 50, 5), sigma=10.0, amplitude=1.0)
        pos_grid = np.stack([X, Y, np.full_like(X, 5)], axis=-1)
        conc_grid = odor.concentration_at(pos_grid.reshape(-1, 3)).reshape(100, 100)
        
        contour = ax.contourf(X, Y, conc_grid, levels=15, cmap='hot', alpha=0.7)
        positions = metrics["positions"]
        ax.plot(positions[:, 0], positions[:, 1], 'c-', linewidth=1, alpha=0.7)
        ax.plot(positions[0, 0], positions[0, 1], 'go', markersize=8)
        ax.plot(positions[-1, 0], positions[-1, 1], 'r*', markersize=12)
        ax.plot(50, 50, 'b*', markersize=18)
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title(strategy['label'])
        ax.set_xlim([0, 100])
        ax.set_ylim([0, 100])
        
        results_summary.append({
            "label": strategy['label'],
            "final_distance": metrics["final_distance"],
            "min_distance": metrics["min_distance"],
            "total_distance": metrics["total_distance"],
        })
    
    plt.tight_layout()
    plt.savefig('outputs/strategy_comparison.png', dpi=100)
    print(f"\n✓ Comparación guardada: outputs/strategy_comparison.png")
    plt.show()
    
    # Tabla resumen
    print("\n" + "="*60)
    print("RESUMEN COMPARATIVO")
    print("="*60)
    print(f"{'Estrategia':<30} {'Dist. Final (mm)':<20} {'Dist. Mín. (mm)':<20}")
    print("-"*70)
    for result in results_summary:
        print(f"{result['label']:<30} {result['final_distance']:<20.1f} {result['min_distance']:<20.1f}")


if __name__ == "__main__":
    # Crear directorio de output
    Path("outputs/olfactory").mkdir(parents=True, exist_ok=True)
    
    # Ejemplo 1: Navegación simple
    print("\n" + "▪"*60)
    print("EJEMPLO 1: Navegación con cerebro binario")
    print("▪"*60)
    metrics = simulate_navigation(
        brain_mode="binary",
        threshold=0.1,
        duration_seconds=20
    )
    
    # Ejemplo 2: Comparar estrategias
    print("\n" + "▪"*60)
    print("EJEMPLO 2: Comparación de estrategias")
    print("▪"*60)
    compare_strategies()
    
    print("\n✓ Ejemplos completados. Revisa outputs/olfactory/ para resultados.")
