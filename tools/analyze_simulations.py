"""
Análisis visual de resultados: Gráficas útiles para diagnóstico

⚠️ DEPRECATED: Consider using analyze_experiments.py for batch analysis
or tools/analysis/generate_improved_report.py for comprehensive reports.

This script provides detailed analysis of individual simulation trajectories.
Use for single-simulation deep-dive analysis only.
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from olfaction.odor_field import OdorField


def load_simulation_data(sim_dir):
    """Cargar datos de simulación desde CSV"""
    
    trajectory_file = Path(sim_dir) / "trajectory.csv"
    data = {
        "step": [],
        "x": [],
        "y": [],
        "z": [],
        "odor": [],
        "forward": [],
        "turn": [],
        "distance": []
    }
    
    with open(trajectory_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data["step"].append(int(row["step"]))
            data["x"].append(float(row["x_mm"]))
            data["y"].append(float(row["y_mm"]))
            data["z"].append(float(row["z_mm"]))
            data["odor"].append(float(row["odor_conc"]))
            data["forward"].append(float(row["forward_cmd"]))
            data["turn"].append(float(row["turn_cmd"]))
            data["distance"].append(float(row["distance_to_source_mm"]))
    
    return {k: np.array(v) for k, v in data.items()}


def plot_simulation_analysis(sim_dir, output_file):
    """Crear gráficas de análisis para una simulación"""
    
    # Cargar datos
    data = load_simulation_data(sim_dir)
    with open(Path(sim_dir) / "config.json", 'r') as f:
        config = json.load(f)
    
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(3, 3, figure=fig)
    
    # 1. Trayectoria en arena
    ax1 = fig.add_subplot(gs[0:2, 0:2])
    
    # Campo de olor como fondo
    x_field = np.linspace(0, 100, 50)
    y_field = np.linspace(0, 100, 50)
    X, Y = np.meshgrid(x_field, y_field)
    pos_grid = np.stack([X, Y, np.full_like(X, 5)], axis=-1)
    
    odor_field = OdorField(
        sources=(50, 50, 5),
        sigma=config.get("sigma", 15),
        amplitude=config.get("amplitude", 1)
    )
    Z = odor_field.concentration_at(pos_grid.reshape(-1, 3)).reshape(50, 50)
    
    contour = ax1.contourf(X, Y, Z, levels=15, cmap='YlOrRd', alpha=0.7)
    ax1.plot(data["x"], data["y"], 'b-', linewidth=1.5, alpha=0.6, label="Trayectoria")
    ax1.plot(data["x"][0], data["y"][0], 'go', markersize=12, label="Inicio")
    ax1.plot(data["x"][-1], data["y"][-1], 'r*', markersize=15, label="Final")
    ax1.plot(50, 50, 'b*', markersize=20, label="Fuente")
    
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 100)
    ax1.set_xlabel("X (mm)")
    ax1.set_ylabel("Y (mm)")
    ax1.set_title("Trayectoria en Arena")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)
    plt.colorbar(contour, ax=ax1, label="Concentración")
    
    # 2. Distancia a la fuente
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.plot(data["step"], data["distance"], 'g-', linewidth=2)
    ax2.axhline(y=data["distance"][0], color='g', linestyle='--', alpha=0.5, label="Inicial")
    ax2.axhline(y=data["distance"][-1], color='r', linestyle='--', alpha=0.5, label="Final")
    ax2.set_xlabel("Paso")
    ax2.set_ylabel("Distancia (mm)")
    ax2.set_title("Distancia a Fuente")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # 3. Concentración detectada
    ax3 = fig.add_subplot(gs[1, 2])
    ax3.plot(data["step"], data["odor"], 'orange', linewidth=1, alpha=0.8)
    ax3.fill_between(data["step"], data["odor"], alpha=0.3, color='orange')
    ax3.set_xlabel("Paso")
    ax3.set_ylabel("Concentración")
    ax3.set_title("Odor Detectado")
    ax3.grid(True, alpha=0.3)
    
    # 4. Comandos motores - Forward
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(data["step"], data["forward"], 'b-', linewidth=1)
    ax4.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax4.set_xlabel("Paso")
    ax4.set_ylabel("Comando Forward")
    ax4.set_title("Control Forward")
    ax4.set_ylim(-1.5, 1.5)
    ax4.grid(True, alpha=0.3)
    
    # 5. Comandos motores - Turn
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(data["step"], data["turn"], 'r-', linewidth=1)
    ax5.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax5.set_xlabel("Paso")
    ax5.set_ylabel("Comando Turn")
    ax5.set_title("Control Turn")
    ax5.set_ylim(-1.5, 1.5)
    ax5.grid(True, alpha=0.3)
    
    # 6. Estadísticas
    ax6 = fig.add_subplot(gs[2, 2])
    ax6.axis('off')
    
    stats_text = f"""
ESTADÍSTICAS

Distancia inicial: {data['distance'][0]:.1f} mm
Distancia final: {data['distance'][-1]:.1f} mm
Mejora: {data['distance'][0] - data['distance'][-1]:.1f} mm

Odor máximo: {np.max(data['odor']):.6f}
Odor promedio: {np.mean(data['odor']):.6f}

Parámetros:
  sigma={config.get('sigma', '?')}
  thresh={config.get('threshold', '?')}
  init=({config.get('initial_position', ['?','?'])[0]}, {config.get('initial_position', ['?','?'])[1]})
    """
    
    ax6.text(0.05, 0.95, stats_text, transform=ax6.transAxes,
             fontsize=10, verticalalignment='top', family='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"    ✓ Gráfica guardada: {output_file.name}")


# =============================================================================
# Analizar todas las simulaciones
# =============================================================================

experiment_dir = Path("outputs") / "Experiment - 2026-03-12_11_59"
simulation_dirs = sorted([d for d in experiment_dir.iterdir() if d.is_dir() and (d / "trajectory.csv").exists()])

print("\n" + "="*70)
print("GENERANDO ANÁLISIS VISUAL")
print("="*70)

for sim_dir in simulation_dirs:
    sim_name = sim_dir.name
    print(f"\n{sim_name}:")
    
    output_file = sim_dir / f"{sim_name}_analysis.png"
    plot_simulation_analysis(sim_dir, output_file)

print("\n" + "="*70)
print(f"✓ Análisis completado")
print(f"  Resultados en: {experiment_dir}/")
print("="*70)
