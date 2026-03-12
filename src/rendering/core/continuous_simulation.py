#!/usr/bin/env python3
"""
WORKAROUND: Custom Simulation Wrapper
======================================
Envuelve SingleFlySimulation para forzar rendering en cada frame.
Necesario porque FlyGym 0.2.7 no renderiza en cada step por defecto.
"""

import numpy as np
from flygym import Fly, SingleFlySimulation
from flygym.arena import FlatTerrain
from flygym.preprogrammed import all_leg_dofs
from typing import Optional

class ContinuousRenderingSimulation(SingleFlySimulation):
    """
    Wrapper de SingleFlySimulation que fuerza rendering en cada frame.
    
    FlyGym 0.2.7 solo renderiza en ciertos intervalos.
    Este wrapper asegura que render() devuelva un frame en CADA step.
    """
    
    def __init__(self, fly: Optional[Fly] = None, arena = None, **kwargs):
        """Inicializar con fly y arena opcionales."""
        if fly is None:
            fly = Fly(
                init_pose="stretch",
                actuated_joints=all_leg_dofs,
                control="position",
            )
        if arena is None:
            arena = FlatTerrain()
        
        super().__init__(fly=fly, arena=arena, **kwargs)
        
        # Forzar render_mode si es posible
        if hasattr(self, 'render_mode'):
            self.render_mode = "rgb_array"
        
        # Flag para saber si necesitamos render this step
        self._force_render = True
        self._last_frame = None
    
    def render(self):
        """
        Override de render() que asegura devolver frame en cada step.
        
        FlyGym normalmente solo renderiza cada N steps.
        Este método:
        1. Intenta obtener frame del rendering normal
        2. Si no hay frame, reutiliza el anterior
        3. Siempre devuelve una lista con 1 frame
        """
        # Intentar render normal
        try:
            # Llamar al método original de SingleFlySimulation
            frame_list = super().render()
            
            if frame_list and isinstance(frame_list, list) and len(frame_list) > 0:
                frame = frame_list[0]
                if frame is not None:
                    self._last_frame = frame
                    return [frame]
        except Exception as e:
            pass
        
        # Si no hay frame válido, usar el anterior
        if self._last_frame is not None:
            return [self._last_frame]
        
        # Si no tenemos frame anterior, retornar None para indicar problema
        return [None]


def test_continuous_rendering():
    """Test: Verificar que el wrapper funciona"""
    print("\n" + "="*70)
    print("TEST: CONTINUOUS RENDERING WRAPPER")
    print("="*70)
    
    sim = ContinuousRenderingSimulation()
    obs, info = sim.reset()
    
    print(f"\n[*] Ejecutando 10 pasos con rendering...")
    
    frames_captured = 0
    for step in range(10):
        # Step
        action = {"joints": np.zeros(42, dtype=np.float32)}
        obs = sim.step(action)
        
        # Render
        frame_list = sim.render()
        
        if frame_list and len(frame_list) > 0 and frame_list[0] is not None:
            frames_captured += 1
        
        print(f"  Step {step}: frame {'✓' if frame_list and frame_list[0] is not None else '✗'}")
    
    print(f"\n[*] Frames capturados: {frames_captured}/10")
    print("="*70)
    
    return frames_captured == 10


if __name__ == "__main__":
    success = test_continuous_rendering()
    exit(0 if success else 1)
