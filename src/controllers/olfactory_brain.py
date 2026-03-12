"""
Módulo de cerebro olfatorio minimalista.

Define la interfaz de decisión que mapea concentración de olor
a acciones motoras (aproximación/fuga).
"""

import numpy as np
from enum import Enum
from typing import Optional


class OlfactoryBrain:
    """
    Cerebro olfatorio simple basado en umbral y memoria temporal.
    
    Convierte una entrada sensorial (concentración de olor) en una salida
    motora 2D que representa velocidad forward y control de giro.
    
    La lógica puede ser binaria (cerca/lejos), gradual (proporcional) o
    con memoria (integrador de gradiente temporal).
    
    Parameters
    ----------
    threshold : float, default=0.1
        Umbral de concentración para activar comportamiento de aproximación.
        Si conc > threshold: aproximarse. Si no: girar o explorar.
    mode : str, default="binary"
        Modo de decisión:
        - "binary": si conc > threshold → avanzar; si no → girar
        - "gradient": salida proporcional a la concentración
        - "temporal_gradient": considera derivada temporal del olor
    forward_scale : float, default=1.0
        Escala de velocidad forward cuando se aproxima.
    turn_scale : float, default=0.5
        Escala de giro cuando no detecta olor o retrocede.
    """
    
    def __init__(
        self,
        threshold: float = 0.1,
        mode: str = "binary",
        forward_scale: float = 1.0,
        turn_scale: float = 0.5,
    ):
        """Inicializar el cerebro olfatorio."""
        self.threshold = threshold
        self.mode = mode
        self.forward_scale = forward_scale
        self.turn_scale = turn_scale
        
        # Historial para cálculos de derivada
        self._odor_history: list = []
        self._max_history = 10  # Mantener últimos 10 pasos
    
    def step(self, odor_concentration: float) -> np.ndarray:
        """
        Ejecutar un paso de decisión del cerebro.
        
        Parameters
        ----------
        odor_concentration : float
            Concentración instantánea en la posición del sensor (0 a 1+).
        
        Returns
        -------
        np.ndarray
            Vector motor 2D [forward, turn]:
            - forward: velocidad hacia adelante (-1 a 1, positivo = avanzar)
            - turn: control de giro (-1 a 1, positivo = girar izquierda)
        """
        # Guardar en historial
        self._odor_history.append(odor_concentration)
        if len(self._odor_history) > self._max_history:
            self._odor_history.pop(0)
        
        if self.mode == "binary":
            return self._step_binary(odor_concentration)
        elif self.mode == "gradient":
            return self._step_gradient(odor_concentration)
        elif self.mode == "temporal_gradient":
            return self._step_temporal_gradient(odor_concentration)
        else:
            raise ValueError(f"Modo desconocido: {self.mode}")
    
    def _step_binary(self, conc: float) -> np.ndarray:
        """
        Decisión binaria: si concentración > umbral, aproximarse.
        Si no, girar para explorar.
        """
        if conc > self.threshold:
            # Aproximarse: avanzar + girar suavemente hacia la fuente
            return np.array([self.forward_scale, 0.0])
        else:
            # Explorar: girar en lugar (o avanzar lentamente)
            return np.array([0.0, self.turn_scale])
    
    def _step_gradient(self, conc: float) -> np.ndarray:
        """
        Salida proporcional a la concentración.
        """
        # Normalizar concentración a [0, 1]
        normalized_conc = np.clip(conc, 0, 1)
        
        # Si hay olor, avanzar con intensidad proporcional
        forward = self.forward_scale * normalized_conc
        
        # Si no hay olor suficiente, girar para buscar
        turn = self.turn_scale * (1 - normalized_conc) if conc < self.threshold else 0.0
        
        return np.array([forward, turn])
    
    def _step_temporal_gradient(self, conc: float) -> np.ndarray:
        """
        Decisión basada en derivada temporal del olor (¿mejorando o empeorando?).
        """
        if len(self._odor_history) < 2:
            # Sin historial suficiente, usar lógica binaria
            return self._step_binary(conc)
        
        # Calcular derivada temporal (simple diferencia)
        odor_derivative = self._odor_history[-1] - self._odor_history[-2]
        
        if conc > self.threshold:
            # Hay olor: aproximarse
            forward = self.forward_scale
        else:
            forward = 0.0
        
        # Si la concentración está aumentando, avanzar en esa dirección
        # Si está disminuyendo, girar para buscar nuevas direcciones
        if odor_derivative > 0:
            # Mejorando: seguir derecho
            turn = 0.0
        else:
            # Empeorando: girar
            turn = self.turn_scale
        
        return np.array([forward, turn])
    
    def get_history(self) -> np.ndarray:
        """Obtener historial de concentraciones registradas."""
        return np.array(self._odor_history)
    
    def reset(self):
        """Limpiar historial (llamar al inicio de cada trial)."""
        self._odor_history.clear()


def test_olfactory_brain():
    """Tests básicos del cerebro olfatorio."""
    
    # Test 1: Modo binario
    brain = OlfactoryBrain(threshold=0.1, mode="binary")
    
    # Concentración baja → giro
    action_low = brain.step(0.05)
    assert action_low[0] == 0.0 and action_low[1] > 0, "Low odor should trigger turn"
    
    # Concentración alta → avanza
    action_high = brain.step(0.5)
    assert action_high[0] > 0 and action_high[1] == 0, "High odor should trigger forward"
    
    # Test 2: Modo gradiente
    brain_grad = OlfactoryBrain(threshold=0.1, mode="gradient")
    
    action_zero = brain_grad.step(0.0)
    action_half = brain_grad.step(0.5)
    action_full = brain_grad.step(1.0)
    
    # Forward aumenta con concentración
    assert action_zero[0] < action_half[0] < action_full[0], "Forward should increase with odor"
    
    # Test 3: Reset
    brain.reset()
    assert len(brain.get_history()) == 0, "History should be empty after reset"
    
    print("✓ Todas las pruebas de OlfactoryBrain pasaron.")


if __name__ == "__main__":
    test_olfactory_brain()
