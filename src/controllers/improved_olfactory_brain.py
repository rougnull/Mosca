"""
Controlador olfatorio MEJORADO con verdadera quimiotaxis bilateral.

ARREGLO CRÍTICO (2026-03-12):
- Problema: La mosca se acercaba al olor pero luego se alejaba al estar cerca
- Causa: Forward se basaba en concentración absoluta, no en cambio temporal
- Solución: Forward ahora usa d(concentración)/dt (temporal gradient)
  * Motor forward activa solo cuando concentración AUMENTA
  * Esto previene que la mosca siga caminando cuando está en la fuente
  * La mosca ahora hace circulos en la fuente en lugar de overshooting

La mosca ahora:
1. Sensea olor en la posición actual
2. Simula sensar en posición "izquierda" y "derecha"
3. Compara gradiente bilateral para decidir hacia dónde girar
4. Avanza solo cuando concentración está AUMENTANDO (temporal gradient)
"""

import numpy as np
from typing import Optional


class ImprovedOlfactoryBrain:
    """
    Cerebro olfatorio con detección de gradiente bilateral simulado
    y control temporal de forward.
    
    Implementa verdadera quimiotaxis positiva:
    - Detecta diferencia bilateral: derecha vs izquierda → Controls turn
    - Detecta cambio temporal: dC/dt → Controls forward
    - Si conc está aumentando: caminar hacia adelante
    - Si conc está disminuyendo: parar o hacer backup
    - Si conc está estable: solo girar hacia el gradiente
    """
    
    def __init__(
        self,
        bilateral_distance: float = 1.2,  # mm: distancia entre antenas (biológico: ~1.2mm)
        forward_scale: float = 1.0,
        turn_scale: float = 0.8,
        threshold: float = 0.01,
        temporal_gradient_gain: float = 10.0,  # Ganancia para dC/dt → forward
    ):
        """
        Inicializar cerebro olfatorio bilateral con temporal gradient.

        Parameters
        ----------
        bilateral_distance : float, default=1.2
            Distancia entre puntos de sensado izquierdo/derecho (mm).
            Simula distancia entre antenas de Drosophila (~1.2mm real).
        forward_scale : float, default=1.0
            Escala de velocidad forward. Con 1.0, forward=1.0 corresponde a
            ~10 mm/s (velocidad típica de marcha de Drosophila).
        turn_scale : float, default=0.8
            Escala de giro basado en gradiente lateral bilateral.
        threshold : float, default=0.01
            Umbral mínimo de concentración normalizada para activar (0-1).
        temporal_gradient_gain : float, default=10.0
            Ganancia aplicada al cambio temporal de concentración.
            Amplifica dC/dt para generar señal forward adecuada.
        """
        self.bilateral_distance = bilateral_distance
        self.forward_scale = forward_scale
        self.turn_scale = turn_scale
        self.threshold = threshold
        self.temporal_gradient_gain = temporal_gradient_gain
        
        self._concentration_history = []
        self._max_history = 20
        self._debug_step_count = 0  # DEBUG: Track calls
    
    def step(
        self,
        odor_field,
        current_position: np.ndarray,
        heading_radians: float
    ) -> np.ndarray:
        """
        Ejecutar paso de decisión con gradiente temporal + bilateral.
        
        Parameters
        ----------
        odor_field : OdorField
            Campo de olor del entorno.
        current_position : np.ndarray
            Posición actual (x, y, z).
        heading_radians : float
            Orientación actual en radianes.
        
        Returns
        -------
        np.ndarray
            Vector motor [forward, turn]
            - forward: basado en CAMBIO temporal de concentración (d C/dt)
            - turn: basado en DIFERENCIA bilateral del gradient
        """
        # DEBUG: Print inputs on first few steps
        self._debug_step_count += 1
        if self._debug_step_count <= 3:
            print(f"\n[Brain Step {self._debug_step_count}]")
            print(f"  Position: {current_position}")
            print(f"  Heading: {heading_radians:.4f} rad ({np.degrees(heading_radians):.1f}°)")

        # 1. Sensear concentración en centro
        conc_center = float(odor_field.concentration_at(current_position))
        
        # 2. Sensear en puntos laterales (bilaterales)
        #    Perpendicular a la dirección del heading actual
        left_angle = heading_radians + np.pi / 2  # 90° a la izquierda
        right_angle = heading_radians - np.pi / 2  # 90° a la derecha
        
        left_pos = current_position + self.bilateral_distance * np.array([
            np.cos(left_angle),
            np.sin(left_angle),
            0
        ])
        right_pos = current_position + self.bilateral_distance * np.array([
            np.cos(right_angle),
            np.sin(right_angle),
            0
        ])
        
        conc_left = float(odor_field.concentration_at(left_pos))
        conc_right = float(odor_field.concentration_at(right_pos))
        
        # 3. Calcular CAMBIO TEMPORAL de concentración
        # CRÍTICO FIX: forward ∝ d(conc)/dt, NO conc absoluta
        # Esto previene que la mosca siga caminando cuando está en la fuente
        if len(self._concentration_history) > 1:
            # Use temporal gradient when we have history
            conc_change = conc_center - self._concentration_history[-1]
        elif len(self._concentration_history) == 1:
            # On second step, use absolute concentration as bootstrap
            # (Assume movement started from 0 concentration to current)
            conc_change = conc_center * 0.5  # Use fraction of absolute conc to bootstrap
        else:
            # FIRST STEP: Use small constant to initiate movement (cold start)
            # Without this, the fly never moves and we get stuck at 0
            # Use larger value (0.5) to ensure sufficient initial movement
            conc_change = 0.5  # Positive value to bootstrap forward movement
        
        # Guardar en historial
        self._concentration_history.append(conc_center)
        if len(self._concentration_history) > self._max_history:
            self._concentration_history.pop(0)
        
        # 4. Calcular diferencia bilateral de gradiente (espacial)
        gradient_difference = conc_left - conc_right

        # DEBUG: Print concentration values on first few steps
        if self._debug_step_count <= 3:
            print(f"  Conc center: {conc_center:.6f}")
            print(f"  Conc left: {conc_left:.6f}")
            print(f"  Conc right: {conc_right:.6f}")
            print(f"  Gradient diff (L-R): {gradient_difference:.6f}")
            print(f"  Conc change: {conc_change if 'conc_change' in locals() else 'N/A'}")

        # 5. Generar acciones motoras:
        
        # FORWARD: solo cuando concentración está AUMENTANDO
        # Escalar el cambio por temporal_gradient_gain para darle sensibilidad
        forward = self.forward_scale * np.clip(conc_change * self.temporal_gradient_gain, 0, 1)
        
        # TURN: basado en comparación bilateral
        # conc_left > conc_right → gradiente_difference positivo → girar izquierda (negativo en código)
        # Pero necesitamos verificar el signo
        turn = self.turn_scale * np.clip(gradient_difference, -1, 1)

        # DEBUG: Print outputs on first few steps
        if self._debug_step_count <= 3:
            print(f"  Motor signal: forward={forward:.6f}, turn={turn:.6f}")

        return np.array([forward, turn])
    
    def get_diagnostics(self) -> dict:
        """Obtener información de diagnóstico del cerebro."""
        if not self._concentration_history:
            return {
                "mean_concentration": 0.0,
                "max_concentration": 0.0,
                "history_length": 0,
            }
        
        conc_arr = np.array(self._concentration_history)
        return {
            "mean_concentration": float(np.mean(conc_arr)),
            "max_concentration": float(np.max(conc_arr)),
            "min_concentration": float(np.min(conc_arr)),
            "history_length": len(self._concentration_history),
        }
