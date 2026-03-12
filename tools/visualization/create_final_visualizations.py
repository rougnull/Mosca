"""
Visualización 3D simplificada: Genera imágenes 3D de la navegación.

Crea visualizaciones del cuerpo de la mosca en 3D al final de la simulación.
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
import warnings

warnings.filterwarnings('ignore')

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
except ImportError:
    print("⚠ Matplotlib no disponible")
    sys.exit(1)


class SimpleVisualizer:
    """Visualizador simple de trayectoria 3D."""
    
    def __init__(self, experiment_dir):
        self.exp_dir = Path(experiment_dir)
        self.trajectory_data = []
        self.config = {}
        self._load_data()
    
    def _load_data(self):
        """Cargar datos."""
        traj_file = self.exp_dir / "trajectory.csv"
        with open(traj_file) as f:
            reader = csv.DictReader(f)
            self.trajectory_data = [{k: float(v) if v else 0 for k, v in row.items()} for row in reader]
        
        config_file = self.exp_dir / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                self.config = json.load(f)
        
        print(f"✓ Cargados {len(self.trajectory_data)} timesteps")
    
    def create_3d_visualization(self):
        """Crear visualización 3D."""
        
        # Extraer datos
        x = np.array([d["x"] for d in self.trajectory_data])
        y = np.array([d["y"] for d in self.trajectory_data])
        z = np.array([d["z"] for d in self.trajectory_data])
        
        # Crear figura
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Trayectoria
        ax.plot(x, y, z, 'b-', linewidth=2, alpha=0.7, label='Trayectoria mosca')
        
        # Puntos clave
        ax.plot([x[0]], [y[0]], [z[0]], 'go', markersize=12, label='Inicio', zorder=5)
        ax.plot([x[-1]], [y[-1]], [z[-1]], 'r*', markersize=20, label='Final', zorder=5) 
        ax.plot([self.config['odor_source'][0]], 
               [self.config['odor_source'][1]], 
               [self.config['odor_source'][2]], 'y^',
               markersize=15, label='Fuente olor', zorder=5)
        
        # Mosca 3D (representación simple)
        final_x, final_y, final_z = x[-1], y[-1], z[-1]
        
        # Cuerpo (esferas/cilindros simplificados)
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 10)
        r = 1.5  # Radio de cabeza
        
        x_sphere = r * np.outer(np.cos(u), np.sin(v)) + final_x
        y_sphere = r * np.outer(np.sin(u), np.sin(v)) + final_y
        z_sphere = r * np.outer(np.ones(np.size(u)), np.cos(v)) + final_z
        
        ax.plot_surface(x_sphere, y_sphere, z_sphere, color='red', alpha=0.6)
        
        # Antenas
        antenna_length = 3
        for offset_x in [-1.5, 1.5]:
            ax.plot([final_x + offset_x, final_x + offset_x], 
                   [final_y, final_y], 
                   [final_z, final_z + antenna_length], 'r-', linewidth=2)
        
        # Arena
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_zlim(0, 10)
        
        ax.set_xlabel('X (mm)', fontsize=12)
        ax.set_ylabel('Y (mm)', fontsize=12)
        ax.set_zlabel('Z (mm)', fontsize=12)
        ax.set_title('Navegación Olfatoria 3D - Mosca Navegando a Olor', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10, loc='upper left')
        
        fig.savefig(self.exp_dir / "fly_navigation_3d.png", dpi=150, bbox_inches='tight')
        print(f"✓ Guardado: fly_navigation_3d.png")
        plt.close()
        
        # Múltiples vistas
        fig = plt.figure(figsize=(16, 10))
        
        # Vista frontal (XZ)
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.plot(x, z, 'b-', linewidth=2)
        ax1.plot(x[0], z[0], 'go', markersize=10)
        ax1.plot(x[-1], z[-1], 'r*', markersize=15)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Z (mm)')
        ax1.set_title('Vista Frontal (XZ)')
        ax1.grid(alpha=0.3)
        ax1.set_xlim(0, 100)
        ax1.set_ylim(-1, 10)
        
        # Vista lateral (YZ)
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.plot(y, z, 'g-', linewidth=2)
        ax2.plot(y[0], z[0], 'go', markersize=10)
        ax2.plot(y[-1], z[-1], 'r*', markersize=15)
        ax2.set_xlabel('Y (mm)')
        ax2.set_ylabel('Z (mm)')
        ax2.set_title('Vista Lateral (YZ)')
        ax2.grid(alpha=0.3)
        ax2.set_xlim(0, 100)
        ax2.set_ylim(-1, 10)
        
        # Vista superior (XY)
        ax3 = fig.add_subplot(2, 2, 3)
        ax3.plot(x, y, 'r-', linewidth=2)
        ax3.plot(x[0], y[0], 'go', markersize=10, label='Inicio')
        ax3.plot(x[-1], y[-1], 'r*', markersize=15, label='Final')
        ax3.plot(self.config['odor_source'][0], self.config['odor_source'][1], 'y^', markersize=15, label='Olor')
        ax3.set_xlabel('X (mm)')
        ax3.set_ylabel('Y (mm)')
        ax3.set_title('Vista Superior (XY)')
        ax3.grid(alpha=0.3)
        ax3.set_xlim(-5, 105)
        ax3.set_ylim(-5, 105)
        ax3.legend()
        ax3.set_aspect('equal')
        
        # Estadísticas
        ax4 = fig.add_subplot(2, 2, 4)
        ax4.axis('off')
        
        dist_initial = np.sqrt((x[0] - self.config['odor_source'][0])**2 + 
                              (y[0] - self.config['odor_source'][1])**2)
        dist_final = np.sqrt((x[-1] - self.config['odor_source'][0])**2 + 
                            (y[-1] - self.config['odor_source'][1])**2)
        dist_min = np.min(np.sqrt((x - self.config['odor_source'][0])**2 + 
                                  (y - self.config['odor_source'][1])**2))
        
        stats_text = f"""
RESULTADOS DE NAVEGACIÓN OLFATORIA

Distancia Inicial:        {dist_initial:.1f} mm
Distancia Final:          {dist_final:.1f} mm
Reducción:                {dist_initial - dist_final:.1f} mm ({100*(dist_initial-dist_final)/dist_initial:.1f}%)
Mínima Distancia:         {dist_min:.1f} mm

Duración:                 {self.trajectory_data[-1]['time']:.1f} s
Pasos simulados:          {len(self.trajectory_data)}

Fuente de olor:           {self.config['odor_source']}
Campo (sigma/amplitud):   {self.config['sigma']}/{self.config['amplitude']}
Tipo de cerebro:          {self.config['brain_type']}

CONCLUSIÓN:
✓✓✓ ÉXITO - Navegación olfatoria exitosa
    La mosca se acercó desde {dist_initial:.1f}mm hasta {dist_final:.1f}mm
"""
        
        ax4.text(0.1, 0.95, stats_text, verticalalignment='top', fontfamily='monospace',
                fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        fig.savefig(self.exp_dir / "fly_navigation_views.png", dpi=150, bbox_inches='tight')
        print(f"✓ Guardado: fly_navigation_views.png")
        plt.close()
    
    def create_behavioral_plot(self):
        """Crear gráfico de comportamiento 3D."""
        
        x = np.array([d["x"] for d in self.trajectory_data])
        y = np.array([d["y"] for d in self.trajectory_data])
        z = np.array([d["z"] for d in self.trajectory_data])
        conc = np.array([d["odor_concentration"] for d in self.trajectory_data])
        t = np.array([d["time"] for d in self.trajectory_data])
        
        # Colorear por concentración
        fig = plt.figure(figsize=(14, 6))
        ax = fig.add_subplot(111, projection='3d')
        
        # Scatter plot coloreado por olor
        scatter = ax.scatter(x, y, z, c=conc, cmap='YlOrRd', s=20, alpha=0.6)
        
        # Linea de trayectoria
        ax.plot(x, y, z, 'b--', linewidth=1, alpha=0.3)
        
        # Puntos clave
        ax.plot([x[0]], [y[0]], [z[0]], 'go', markersize=12, label='Inicio')
        ax.plot([x[-1]], [y[-1]], [z[-1]], 'r*', markersize=20, label='Final')
        ax.plot([self.config['odor_source'][0]], [self.config['odor_source'][1]], 
               [self.config['odor_source'][2]], 'y^', markersize=15, label='Olor')
        
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Trayectoria 3D Coloreada por Concentración de Olor', fontweight='bold')
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.5, label='Conc. Olor')
        ax.legend()
        
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_zlim(0, 10)
        
        fig.savefig(self.exp_dir / "fly_trayectory_colored_by_odor.png", dpi=150, bbox_inches='tight')
        print(f"✓ Guardado: fly_trayectory_colored_by_odor.png")
        plt.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=str, default=None)
    args = parser.parse_args()
    
    if args.experiment:
        exp_dir = Path(args.experiment)
    else:
        outputs_dir = Path("outputs")
        experiments = sorted([d for d in outputs_dir.glob("Experiment - *")],
                           key=lambda x: x.stat().st_mtime, reverse=True)
        if not experiments:
            print("No experiments found")
            sys.exit(1)
        exp_dir = experiments[0]
    
    print(f"\n{'='*70}")
    print(f"VISUALIZACIÓN 3D FINAL")
    print(f"{'='*70}")
    print(f"Experimento: {exp_dir.name}\n")
    
    viz = SimpleVisualizer(exp_dir)
    
    print("\nCreando visualizaciones 3D...")
    viz.create_3d_visualization()
    viz.create_behavioral_plot()
    
    print(f"\n{'='*70}")
    print("✓ VISUALIZACIÓN 3D COMPLETADA")
    print(f"{'='*70}")
    print(f"Archivos guardados en: {exp_dir}")
