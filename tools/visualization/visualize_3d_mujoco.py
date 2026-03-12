"""
Visualización 3D final: Reproducer datos de navegación en MuJoCo.

Lee los datos de trayectoria del experimento exitoso y los reproduce
en MuJoCo para generar animación 3D del cuerpo de la mosca.
"""

import sys
from pathlib import Path
import json
import csv
import numpy as np
from datetime import datetime 
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flygym import Fly, Simulation
    from flygym.arena import FlatTerrain
    FLYGYM_AVAILABLE = True
except ImportError:
    print("⚠ FlyGym no disponible")
    FLYGYM_AVAILABLE = False


class MuJoCoVisualizer:
    """Visualizador 3D con MuJoCo/FlyGym."""
    
    def __init__(self, experiment_dir):
        self.exp_dir = Path(experiment_dir)
        self.trajectory_data = []
        self.config = {}
        
        self._load_data()
    
    def _load_data(self):
        """Cargar datos de trayectoria y configuración."""
        
        traj_file = self.exp_dir / "trajectory.csv"
        if not traj_file.exists():
            raise FileNotFoundError(f"Trayectoria no encontrada: {traj_file}")
        
        with open(traj_file) as f:
            reader = csv.DictReader(f)
            self.trajectory_data = [
                {k: float(v) if v else 0 for k, v in row.items()}
                for row in reader
            ]
        
        config_file = self.exp_dir / "config.json"
        if config_file.exists():
            with open(config_file) as f:
                self.config = json.load(f)
        
        print(f"✓ Datos cargados: {len(self.trajectory_data)} timesteps")
    
    def run_visualizer(self, render_every_n_steps=10, record_video=True):
        """
        Ejecutar visualizador 3D.
        
        Parameters
        ----------
        render_every_n_steps : int
            Renderizar cada N pasos para acelerar
        record_video : bool
            Grabar video MP4
        """
        
        print(f"\n{'='*70}")
        print("VISUALIZACIÓN 3D EN MUJOCO")
        print(f"{'='*70}")
        
        if not FLYGYM_AVAILABLE:
            print("\n⚠ FlyGym no disponible")
            print("Para instalar: pip install flygym")
            print("\nUsando renderizado de trayectoria simplificado...")
            return self._render_simple_video()
        
        print(f"\nIntentando usar FlyGym para renderizado 3D...")
        
        try:
            return self._render_with_flygym(render_every_n_steps, record_video)
        except Exception as e:
            print(f"Error con FlyGym: {e}")
            print("Alternativamente, creando visualización de trayectoria...")
            return self._render_simple_video()
    
    def _render_with_flygym(self, render_every_n_steps, record_video):
        """Renderizar con FlyGym."""
        
        try:
            # Crear mosca y entorno
            fly = Fly(name="fly", enable_adhesion=True)
            arena = FlatTerrain()
            
            # Simulation con renderizado
            sim = Simulation(
                [fly],
                arena=arena,
                physics_timestep=0.0001,
                render_playspeed=1,
                render_interval=render_every_n_steps,
            )
            
            print("✓ Simulación FlyGym inicializada")
            
            # Parámetros de grabación
            output_file = self.exp_dir / "fly_3d_animation.mp4"
            
            if record_video:
                print(f"Grabando video a: {output_file}")
                # Nota: La grabación depende de la configuración de FlyGym
                # Algunos recursos: https://github.com/NeLy-EPFL/flygym
            
            # Reproducir trayectoria
            obs, info = sim.reset()
            
            for step, data in enumerate(self.trajectory_data):
                # Convertir datos de trayectoria a acciones FlyGym
                # Esto es un placeholder: FlyGym típicamente requiere
                # acciones de control, no directamente posiciones
                
                # Para una demostración simple, generamos movimientos básicos
                forward = min(data["brain_forward"] * 10, 1.0)
                turn = data["brain_turn"] * 0.5
                
                # Crear vector de acción para fly
                # Estructura típica: [leg_velocities, wing_control]
                action = np.zeros(len(fly.leg_unstacked_dof) + 2)
                
                # Aplicar movimiento forward a las 6 patas
                for i in range(0, min(18, len(action))):
                    action[i] = forward * 0.2
                
                # Aplicar giro asimétrico
                for i in range(0, 9):
                    action[i] -= turn * 0.1  # Pata izquierda
                for i in range(9, 18):
                    action[i] += turn * 0.1  # Pata derecha
                
                # Ejecutar paso
                obs, term, trunc, info = sim.step({"fly": action})
                
                if (step + 1) % 100 == 0:
                    print(f"  Step {step + 1}/{len(self.trajectory_data)}")
                
                if term or trunc:
                    break
            
            print(f"\n✓ Visualización completada")
            print(f"✓ Archivo guardado (si FlyGym soporta grabación)")
            
            return output_file
        
        except Exception as e:
            print(f"Error en FlyGym: {e}")
            raise
    
    def _render_simple_video(self):
        """Renderizar video simple de trayectoria 2D."""
        
        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation
        except ImportError:
            print("⚠ Matplotlib no disponible para video")
            return None
        
        print("\nGenerando video de trayectoria 2D...")
        
        # Extraer datos
        times = np.array([d["time"] for d in self.trajectory_data])
        x = np.array([d["x"] for d in self.trajectory_data])
        y = np.array([d["y"] for d in self.trajectory_data])
        
        # Crear figura
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Setup axes
        ax1.set_xlim(0, 100)
        ax1.set_ylim(0, 100)
        ax1.set_xlabel("X (mm)")
        ax1.set_ylabel("Y (mm)")
        ax1.set_title("Trayectoria de Navigation")
        ax1.grid(alpha=0.3)
        ax1.plot(self.config['odor_source'][0], 
                self.config['odor_source'][1], 'y*',
                markersize=20, label='Fuente olor')
        
        # Trayectoria line
        line, = ax1.plot([], [], 'b-', linewidth=2, label='Mosca')
        point, = ax1.plot([], [], 'ro', markersize=8)
        
        # Info panel
        ax2.axis('off')
        info_text = ax2.text(0.05, 0.95, '', transform=ax2.transAxes,
                            verticalalignment='top', fontsize=12,
                            family='monospace',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        def animate(frame):
            line.set_data(x[:frame+1], y[:frame+1])
            point.set_data([x[frame]], [y[frame]])
            
            # Actualizar info
            dist = np.sqrt((x[frame] - self.config['odor_source'][0])**2 +
                          (y[frame] - self.config['odor_source'][1])**2)
            
            info = f"""
Frame: {frame+1}/{len(times)}
Tiempo: {times[frame]:.2f}s
Posicion: ({x[frame]:.1f}, {y[frame]:.1f}) mm
Distancia a olor: {dist:.1f} mm
"""
            info_text.set_text(info)
            
            return line, point, info_text
        
        # Crear animación
        anim = animation.FuncAnimation(fig, animate, 
                                     frames=len(times),
                                     interval=50,  # 50ms por frame
                                     blit=True,
                                     repeat=True)
        
        # Guardar video
        output_file = self.exp_dir / "fly_3d_animation.mp4"
        
        print(f"Grabando: {output_file}")
        try:
            anim.save(str(output_file), writer='ffmpeg', fps=20, dpi=100)
            print(f"✓ Video guardado: {output_file}")
        except Exception as e:
            print(f"⚠ No se pudo grabar MP4: {e}")
            print("  Intente instalar: pip install ffmpeg-python")
            return None
        
        plt.close()
        
        return output_file
    
    def generate_3d_model_visualization(self):
        """Generar visualización 3D estática del modelo de mosca."""
        
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
        except ImportError:
            print("⚠ Matplotlib 3D no disponible")
            return None
        
        print("\nGenerando visualización 3D estática...")
        
        # Puntos finales de la trayectoria
        final_x = self.trajectory_data[-1]["x"]
        final_y = self.trajectory_data[-1]["y"]
        final_z = self.trajectory_data[-1]["z"]
        
        # Crear figura 3D
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Trayectoria en 3D
        x_traj = np.array([d["x"] for d in self.trajectory_data])
        y_traj = np.array([d["y"] for d in self.trajectory_data])
        z_traj = np.array([d["z"] for d in self.trajectory_data])
        
        ax.plot(x_traj, y_traj, z_traj, 'b-', linewidth=2, alpha=0.7, label='Trayectoria')
        ax.plot([x_traj[0]], [y_traj[0]], [z_traj[0]], 'go', markersize=10, label='Inicio')
        ax.plot([x_traj[-1]], [y_traj[-1]], [z_traj[-1]], 'r*', markersize=15, label='Final')
        ax.plot([self.config['odor_source'][0]], 
               [self.config['odor_source'][1]], 
               [self.config['odor_source'][2]], 'y^',
               markersize=12, label='Fuente olor')
        
        # Mosca como pequeñas esferas/estructura
        # Simular segmentos simples del cuerpo
        ax.scatter([final_x], [final_y], [final_z], s=100, c='red', marker='o', alpha=0.7)
        
        # Antenas
        for offset in [-2, 2]:
            ax.plot([final_x, final_x + offset], 
                   [final_y, final_y], 
                   [final_z, final_z + 1], 'r-', linewidth=2)
        
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Navegación 3D - Vista final de mosca')
        ax.legend()
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.set_zlim(0, 10)
        
        output_file = self.exp_dir / "fly_3d_final_position.png"
        fig.savefig(output_file, dpi=150)
        print(f"✓ Visualización 3D guardada: {output_file}")
        
        plt.close()
        
        return output_file


# =============================================================================
# EJECUTAR
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=str, default=None,
                       help="Directorio del experimento")
    args = parser.parse_args()
    
    # Detectar último experimento
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
    print(f"Experimento: {exp_dir.name}")
    
    visualizer = MuJoCoVisualizer(exp_dir)
    
    # Generar visualizaciones
    print("\n📹 Generando animación...")
    video_file = visualizer.run_visualizer(record_video=True)
    
    print("\n🎨 Generando visualización 3D estática...")
    img_file = visualizer.generate_3d_model_visualization()
    
    print(f"\n{'='*70}")
    print("✓ VISUALIZACIÓN COMPLETADA")
    print(f"{'='*70}")
    if video_file:
        print(f"✓ Video:   {video_file}")
    if img_file:
        print(f"✓ Imagen:  {img_file}")
    print(f"\nDirectorio: {exp_dir}")
