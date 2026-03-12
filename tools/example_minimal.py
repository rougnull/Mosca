#!/usr/bin/env python3
"""
=============================================================================
EJEMPLO MINIMALISTA: Navegación Olfatoria
=============================================================================

Script más simple posible demostrando los 3 componentes:
1. Campo de olor (OdorField)
2. Cerebro de decisión (OlfactoryBrain)  
3. Simulación básica

Requiere: numpy, matplotlib (sin FlyGym)
Tiempo de ejecución: ~5 segundos
Salida: gráficas en outputs/

Para correr:
    python example_minimal.py
"""

import sys
from pathlib import Path
import numpy as np

# Importar módulos
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain


def main():
    """Ejemplo minimalista en 50 líneas."""
    
    print("\n" + "="*70)
    print("EJEMPLO MINIMALISTA: Navegación Olfatoria")
    print("="*70 + "\n")
    
    # ==================== 1. CREAR CAMPO DE OLOR ====================
    print("1. Creando campo de olor en (50, 50, 5) mm...", end=" ")
    odor = OdorField(
        sources=(50, 50, 5),  # Posición de fuente en mm
        sigma=10,              # Ancho del gradiente
        amplitude=1.0          # Intensidad máxima
    )
    print("✓")
    
    # ==================== 2. CREAR CEREBRO ====================
    print("2. Creando cerebro olfatorio (modo binario)...", end=" ")
    brain = OlfactoryBrain(
        threshold=0.1,          # Umbral para activar aproximación
        mode="binary",          # Otros: "gradient", "temporal_gradient"
        forward_scale=1.0,      # Velocidad forward
        turn_scale=0.5          # Velocidad de giro
    )
    print("✓")
    
    # ==================== 3. SIMULAR MOVIMIENTO ====================
    print("3. Simulando 10 segundos de navegación...")
    
    # Parámetros de simulación
    dt = 0.01                  # 10 ms entre controles
    duration = 10              # 10 segundos
    max_speed = 10             # mm/s
    max_angular_speed = 90     # deg/s
    num_steps = int(duration / dt)
    
    # Inicializar
    position = np.array([20.0, 20.0, 5.0])  # Posición inicial (mm)
    heading = 0.0  # Orientación actual (radianes)
    
    # Almacenar resultados
    positions = [position.copy()]
    odors = []
    actions = []
    
    # Loop de simulación
    for step in range(num_steps):
        # A. Leer concentración en posición actual
        conc = odor.concentration_at(position)
        odors.append(conc)
        
        # B. Cerebro decide acción basada en olor
        action = brain.step(conc)  # Retorna [forward, turn]
        actions.append(action)
        
        # C. Convertir acciones a movimiento
        heading += np.deg2rad(action[1] * max_angular_speed * dt)
        velocity = max_speed * action[0]
        
        # D. Actualizar posición
        delta_x = velocity * np.cos(heading) * dt
        delta_y = velocity * np.sin(heading) * dt
        position = np.array([
            position[0] + delta_x,
            position[1] + delta_y,
            5.0  # z fija
        ])
        
        # E. Mantener dentro de arena (0-100 mm)
        position[:2] = np.clip(position[:2], 0, 100)
        positions.append(position.copy())
    
    positions = np.array(positions)
    odors = np.array(odors)
    actions = np.array(actions)
    
    print(f"   ✓ Completado. {len(positions)} posiciones registradas.")
    
    # ==================== 4. ANALIZAR RESULTADOS ====================
    print("\n4. Resultados:")
    print(f"   Posición inicial: ({positions[0][0]:.1f}, {positions[0][1]:.1f}) mm")
    print(f"   Posición final:   ({positions[-1][0]:.1f}, {positions[-1][1]:.1f}) mm")
    print(f"   Fuente en:        (50, 50) mm")
    
    dist_inicial = np.linalg.norm(positions[0][:2] - np.array([50, 50]))
    dist_final = np.linalg.norm(positions[-1][:2] - np.array([50, 50]))
    print(f"   Distancia inicial a fuente: {dist_inicial:.1f} mm")
    print(f"   Distancia final a fuente:   {dist_final:.1f} mm")
    print(f"   Movimiento: {'Hacia fuente ✓' if dist_final < dist_inicial else 'Alejado de fuente'}")
    
    print(f"\n   Olor máximo detectado: {np.max(odors):.4f}")
    print(f"   Olor medio:           {np.mean(odors):.4f}")
    
    # ==================== 5. VISUALIZAR (opcional) ====================
    try:
        import matplotlib.pyplot as plt
        
        print("\n5. Generando gráficas...")
        
        # Malla de concentración 2D
        x = np.linspace(0, 100, 50)
        y = np.linspace(0, 100, 50)
        X, Y = np.meshgrid(x, y)
        pos_grid = np.stack([X, Y, np.full_like(X, 5)], axis=-1)
        conc_field = odor.concentration_at(pos_grid.reshape(-1, 3)).reshape(50, 50)
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Panel 1: Trayectoria
        ax = axes[0]
        contour = ax.contourf(X, Y, conc_field, levels=15, cmap='hot')
        ax.plot(positions[:, 0], positions[:, 1], 'c-', alpha=0.7, linewidth=1.5)
        ax.plot(positions[0, 0], positions[0, 1], 'go', markersize=10, label='Inicio')
        ax.plot(positions[-1, 0], positions[-1, 1], 'r*', markersize=15, label='Final')
        ax.plot(50, 50, 'b*', markersize=20, label='Fuente')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title('Trayectoria de navegación')
        ax.legend()
        plt.colorbar(contour, ax=ax, label='Concentración olor')
        
        # Panel 2: Concentración y acciones vs tiempo
        ax = axes[1]
        time = np.arange(len(odors)) * dt
        ax.plot(time, odors, 'b-', linewidth=2, label='Concentración')
        ax.set_xlabel('Tiempo (s)')
        ax.set_ylabel('Concentración olor', color='b')
        ax.tick_params(axis='y', labelcolor='b')
        ax.grid(alpha=0.3)
        
        ax2 = ax.twinx()
        ax2.plot(time, actions[:, 0], 'g--', alpha=0.7, label='Forward')
        ax2.set_ylabel('Comando motor', color='g')
        ax2.tick_params(axis='y', labelcolor='g')
        
        ax.set_title('Olor (azul) vs Comando forward (verde)')
        
        plt.tight_layout()
        
        # Guardar
        Path("outputs").mkdir(exist_ok=True)
        filename = "outputs/example_minimal.png"
        plt.savefig(filename, dpi=100)
        print(f"   ✓ Guardado: {filename}")
        
        plt.show()
        
    except ImportError:
        print("\n5. (Matplotlib no disponible, saltando gráficas)")
    
    print("\n" + "="*70)
    print("✓ Ejemplo completado exitosamente")
    print("="*70 + "\n")
    
    return positions, odors, actions


if __name__ == "__main__":
    positions, odors, actions = main()
    
    # Ahora puedes analizar los resultados:
    # - positions: array (N_steps, 3) con trayectoria
    # - odors: array (N_steps,) con concentración registrada
    # - actions: array (N_steps, 2) con [forward, turn]
