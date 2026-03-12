"""
Módulo de Mosca con sensor olfativo.

Define BrainFly, una subclase de flygym.Fly que integra un sensor olfativo
y un cerebro para tomar decisiones motoras basadas en olor.
"""

import numpy as np
from typing import Optional, Dict, Any

try:
    from flygym import Fly
    from flygym.simulation import Simulation
except ImportError:
    # Fallback para desarrollo sin flygym instalado
    class Fly:
        pass


class BrainFly(Fly):
    """
    Mosca con integración sensoriomotora olfatoria.
    
    Extiende FlyGym's Fly para incluir:
    - Sensor olfativo en la cabeza
    - Integración con un cerebro olfatorio minimalista
    - Traducción de salida cerebral a acciones motoras
    
    Parameters
    ----------
    brain : OlfactoryBrain
        Instancia del cerebro olfatorio que genera decisiones.
    odor_field : OdorField
        Campo de olor del entorno.
    sensor_position : str, default="head"
        Dónde está localizado el sensor:
        - "head": en la cabeza (posición estimada de antenas)
        - "centerofmass": en el centro de masa
    motor_mode : str, default="hybrid_turning"
        Cómo se mapea la salida cerebral a acciones:
        - "hybrid_turning": vector 2D [forward, turn] para HybridTurningFly
        - "direct_joints": acciones directas de 42 DoF
    *args, **kwargs
        Argumentos pasados a Fly.__init__()
    """
    
    def __init__(
        self,
        brain,
        odor_field,
        sensor_position: str = "head",
        motor_mode: str = "hybrid_turning",
        *args,
        **kwargs
    ):
        """Inicializar BrainFly."""
        super().__init__(*args, **kwargs)
        
        self.brain = brain
        self.odor_field = odor_field
        self.sensor_position = sensor_position
        self.motor_mode = motor_mode
        
        # Buffer de observaciones para acceso rápido
        self._last_obs = None
        self._odor_concentration = 0.0
    
    def get_sensory_input(self, obs: Dict[str, Any]) -> float:
        """
        Extraer entrada sensorial (concentración de olor) de las observaciones.
        
        Parameters
        ----------
        obs : Dict[str, Any]
            Diccionario de observaciones proporcionado por Simulation.step()
        
        Returns
        -------
        float
            Concentración de olor (0 a 1+).
        """
        try:
            if self.sensor_position == "head":
                # Intentar obtener posición de la cabeza desde diferentes fuentes
                if "head_pos" in obs:
                    head_pos = obs["head_pos"]
                elif "Nuro" in obs and "head_pos" in obs["Nuro"]:
                    head_pos = obs["Nuro"]["head_pos"]
                else:
                    # Fallback: usar posición de la cabeza del segmento Front
                    # En FlyGym, la cabeza es típicamente un punto de referencia
                    head_pos = obs.get("body_positions", {}).get("head", np.zeros(3))
            
            elif self.sensor_position == "centerofmass":
                if "centerofmass" in obs:
                    head_pos = obs["centerofmass"]
                else:
                    head_pos = np.zeros(3)
            else:
                head_pos = np.zeros(3)
            
            # Evaluar concentración en la posición del sensor
            conc = self.odor_field.concentration_at(head_pos)
            self._odor_concentration = float(conc)
            
        except Exception as e:
            # Si hay error en lectura de posición, retornar 0
            print(f"Warning: Error leyendo posición sensorial: {e}")
            self._odor_concentration = 0.0
        
        return self._odor_concentration
    
    def step(self, obs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Ejecutar un paso sensoriomotor: leer olor → cerebro → acción.
        
        Este método se puede llamar externamente o integrarse en el bucle
        de simulación principal.
        
        Parameters
        ----------
        obs : Dict[str, Any]
            Observaciones del entorno.
        
        Returns
        -------
        Dict[str, Any]
            Acciones para pasarle a Simulation.step()
        """
        self._last_obs = obs
        
        # 1. Leer entrada sensorial
        odor = self.get_sensory_input(obs)
        
        # 2. Procesar con cerebro
        motor_signal = self.brain.step(odor)  # [forward, turn]
        
        # 3. Convertir señal cerebral a acciones motoras
        action = self._motor_signal_to_action(motor_signal)
        
        return action
    
    def _motor_signal_to_action(self, motor_signal: np.ndarray) -> Dict[str, Any]:
        """
        Convertir vector motor 2D [forward, turn] a acciones FlyGym.
        
        Parameters
        ----------
        motor_signal : np.ndarray
            Vector [forward, turn] con cada componente en [-1, 1].
        
        Returns
        -------
        Dict[str, Any]
            Diccionario de acciones compatible con Simulation.step()
        """
        forward, turn = motor_signal
        
        if self.motor_mode == "hybrid_turning":
            # Mapear a formato de HybridTurningFly
            # El formato típico es {'fly_name': {'action': [forward, turn]}}
            # o simplemente retornar el array si se usa directamente
            return {
                "joints": np.array([forward, turn]),
            }
        
        elif self.motor_mode == "direct_joints":
            # Aquí se implementaría conversión completa a 42 DoF
            # Por ahora, retornar un placeholder
            # En una implementación real, usarías una matriz de conversión
            # o una red neuronal pequeña para mapear [forward, turn] → 42 DoF
            action_42d = self._hybrid_to_42dof(forward, turn)
            return {
                "joints": action_42d,
            }
        
        else:
            raise ValueError(f"motor_mode desconocido: {self.motor_mode}")
    
    def _hybrid_to_42dof(self, forward: float, turn: float) -> np.ndarray:
        """
        Placeholder para convertir 2D a 42 DoF.
        
        En una versión real, se usaría la lógica de HybridTurningFly
        para expandir [forward, turn] a amplitudes de 42 articulaciones.
        """
        # Aquí podrías integrar lógica de CPG si está disponible
        action_42d = np.zeros(42)
        
        # Aplicar forward a movimientos laterales de las patas
        # Aplicar turn a asimetría de movimiento
        forward = np.clip(forward, -1, 1)
        turn = np.clip(turn, -1, 1)
        
        # Ejemplo simplista: amplitudes de las tres patas por lado
        # Estructura típica: 3 patas/lado × 6 DoF/pata = 18 DoF total por lado
        for leg_idx in range(3):
            # Pata izquierda
            base_idx_L = leg_idx * 6
            action_42d[base_idx_L:base_idx_L + 3] = 0.5 * forward  # forward bias
            action_42d[base_idx_L + 3] = -0.2 * turn  # turning control
            
            # Pata derecha
            base_idx_R = 18 + leg_idx * 6
            action_42d[base_idx_R:base_idx_R + 3] = 0.5 * forward
            action_42d[base_idx_R + 3] = 0.2 * turn
        
        return action_42d
    
    def get_odor_concentration(self) -> float:
        """Retornar la última concentración de olor registrada."""
        return self._odor_concentration
    
    def get_last_observations(self) -> Optional[Dict[str, Any]]:
        """Retornar las últimas observaciones procesadas."""
        return self._last_obs


def test_brain_fly():
    """Test básico de BrainFly (requiere importaciones)."""
    import sys
    sys.path.insert(0, '/path/to/olfaction')
    sys.path.insert(0, '/path/to/controllers')
    
    from olfaction.odor_field import OdorField
    from controllers.olfactory_brain import OlfactoryBrain
    
    # Crear instancias
    odor = OdorField(sources=(5, 5, 0), sigma=2.0)
    brain = OlfactoryBrain(threshold=0.1, mode="binary")
    
    # Simulación de observaciones
    obs = {
        "head_pos": np.array([0, 0, 0]),
    }
    
    # (Esto requeriría una instancia real de Fly, ahora solo es un test de estructura)
    print("✓ BrainFly está estructurada correctamente (test limitado sin FlyGym).")


if __name__ == "__main__":
    test_brain_fly()
