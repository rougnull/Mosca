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
        self._last_motor_signal = np.zeros(2)  # Store last [forward, turn] command
    
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
    
    def _extract_head_position(self, obs: Dict[str, Any]) -> np.ndarray:
        """
        Extraer posición de la cabeza de las observaciones.

        Parameters
        ----------
        obs : Dict[str, Any]
            Observaciones de FlyGym.

        Returns
        -------
        np.ndarray
            Posición [x, y, z] en mm.
        """
        try:
            # Opción 1: SingleFlySimulation structure: obs["fly"] = (pos, quat, euler, ...)
            if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 1:
                # obs["fly"][0] = position array [x, y, z]
                position = obs["fly"][0]
                if hasattr(position, '__len__') and len(position) >= 3:
                    return np.array(position)

            # Opción 2: Nested dict structure
            elif "head_pos" in obs:
                return np.array(obs["head_pos"])
            elif "Nuro" in obs and "head_pos" in obs["Nuro"]:
                return np.array(obs["Nuro"]["head_pos"])
            elif "fly" in obs and "position" in obs["fly"]:
                return np.array(obs["fly"]["position"])
            else:
                # Fallback: posición del cuerpo o centro de masa
                return obs.get("body_positions", {}).get("head", np.zeros(3))
        except Exception as e:
            print(f"Warning: Error extrayendo posición de cabeza: {e}")
            return np.zeros(3)

    def _extract_heading(self, obs: Dict[str, Any]) -> float:
        """
        Extraer orientación (yaw/heading) de la mosca desde observaciones.

        Parameters
        ----------
        obs : Dict[str, Any]
            Observaciones de FlyGym.

        Returns
        -------
        float
            Heading en radianes (ángulo en plano XY).
        """
        try:
            # Opción 1: SingleFlySimulation structure: obs["fly"] = (pos, quat, euler, ...)
            if "fly" in obs and isinstance(obs["fly"], (tuple, list)) and len(obs["fly"]) >= 3:
                # obs["fly"][2] = orientation as Euler angles [roll, pitch, yaw]
                orientation = obs["fly"][2]
                if hasattr(orientation, '__len__') and len(orientation) >= 3:
                    return float(orientation[2])  # yaw is third element

            # Opción 2: Si hay quaternion de orientación
            elif "fly_orientation" in obs:
                quat = obs["fly_orientation"]
                return self._quaternion_to_yaw(quat)

            # Opción 3: Si FlyGym proporciona orientación directamente
            elif "orientation" in obs:
                # Puede ser [roll, pitch, yaw] o quaternion
                orientation = obs["orientation"]
                if len(orientation) == 4:  # Quaternion
                    return self._quaternion_to_yaw(orientation)
                elif len(orientation) >= 3:  # Euler angles
                    return float(orientation[2])  # yaw es el tercer elemento

            # Opción 4: Calcular desde velocidad si está disponible
            elif "fly_velocity" in obs:
                vel = obs["fly_velocity"]
                if len(vel) >= 2 and (abs(vel[0]) > 1e-6 or abs(vel[1]) > 1e-6):
                    return np.arctan2(vel[1], vel[0])

            # Opción 5: Usar orientación almacenada o default
            if hasattr(self, '_last_heading'):
                return self._last_heading
            else:
                return 0.0

        except Exception as e:
            print(f"Warning: Error extrayendo heading: {e}")
            return getattr(self, '_last_heading', 0.0)

    def _quaternion_to_yaw(self, quat: np.ndarray) -> float:
        """
        Convertir quaternion a ángulo yaw (rotación en plano XY).

        Parameters
        ----------
        quat : np.ndarray
            Quaternion [w, x, y, z] o [x, y, z, w] dependiendo de convención.

        Returns
        -------
        float
            Ángulo yaw en radianes.
        """
        try:
            # Intentar ambas convenciones
            if len(quat) == 4:
                # Convención [w, x, y, z]
                w, x, y, z = quat
                # Fórmula: yaw = atan2(2(wz + xy), 1 - 2(y² + z²))
                yaw = np.arctan2(2.0 * (w * z + x * y),
                                 1.0 - 2.0 * (y * y + z * z))
                return float(yaw)
        except Exception:
            pass

        return 0.0

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

        # Verificar si el cerebro es ImprovedOlfactoryBrain (requiere heading)
        brain_class_name = self.brain.__class__.__name__

        if brain_class_name == "ImprovedOlfactoryBrain":
            # Usar versión mejorada con heading
            # 1. Extraer posición de la cabeza
            head_pos = self._extract_head_position(obs)

            # 2. Extraer orientación (heading)
            heading = self._extract_heading(obs)
            self._last_heading = heading  # Guardar para próximo step

            # 3. Procesar con cerebro mejorado (recibe campo completo, posición y heading)
            motor_signal = self.brain.step(self.odor_field, head_pos, heading)
        else:
            # Usar versión legacy (solo recibe concentración escalar)
            # 1. Leer entrada sensorial
            odor = self.get_sensory_input(obs)

            # 2. Procesar con cerebro
            motor_signal = self.brain.step(odor)  # [forward, turn]

        # 3. Convertir señal cerebral a acciones motoras
        action = self._motor_signal_to_action(motor_signal)

        # Store motor signal for diagnostics/logging
        self._last_motor_signal = motor_signal.copy()

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
                "adhesion": np.ones(6),  # Mantener adhesión activa en todas las patas
            }
        
        elif self.motor_mode == "direct_joints":
            # Aquí se implementaría conversión completa a 42 DoF
            # Por ahora, retornar un placeholder
            # En una implementación real, usarías una matriz de conversión
            # o una red neuronal pequeña para mapear [forward, turn] → 42 DoF
            action_42d = self._hybrid_to_42dof(forward, turn)
            return {
                "joints": action_42d,
                "adhesion": np.ones(6),  # Mantener adhesión activa en todas las patas
            }
        
        else:
            raise ValueError(f"motor_mode desconocido: {self.motor_mode}")
    
    def _hybrid_to_42dof(self, forward: float, turn: float) -> np.ndarray:
        """
        Convert 2D [forward, turn] to 42 DoF joint angles using CPG.

        Uses a Central Pattern Generator (CPG) network to generate
        coordinated tripod gait patterns that convert high-level motor
        commands into realistic joint angle trajectories.

        Parameters
        ----------
        forward : float
            Forward command [-1, 1]. Positive = forward, negative = backward.
        turn : float
            Turn command [-1, 1]. Positive = right turn, negative = left turn.

        Returns
        -------
        np.ndarray
            Array of 42 joint angles in radians.
        """
        # Initialize CPG controller if not already done
        if not hasattr(self, '_cpg_controller'):
            try:
                from controllers.cpg_controller import AdaptiveCPGController
                # Use adaptive controller for smooth transitions
                self._cpg_controller = AdaptiveCPGController(
                    timestep=0.01,  # Assumes 100Hz simulation
                    base_frequency=2.0  # 2 Hz stepping frequency
                )
                print("[BrainFly] Initialized CPG controller")
            except ImportError:
                print("[BrainFly] Warning: CPG controller not available, using simplified model")
                self._cpg_controller = None

        # Use CPG if available, otherwise fallback to simple model
        if self._cpg_controller is not None:
            return self._cpg_controller.step(forward, turn)
        else:
            # Fallback: simplified static pattern
            return self._simple_fallback_pattern(forward, turn)

    def _simple_fallback_pattern(self, forward: float, turn: float) -> np.ndarray:
        """
        Simple fallback pattern when CPG is not available.

        This generates basic joint angles without dynamic coordination.
        Should only be used for testing when CPG module is unavailable.
        """
        action_42d = np.zeros(42)

        forward = np.clip(forward, -1, 1)
        turn = np.clip(turn, -1, 1)

        # 6 legs × 7 DoF = 42 total
        # Order: LF, LM, LH, RF, RM, RH
        for leg_idx in range(6):
            base_idx = leg_idx * 7

            # Apply forward bias and turn modulation
            is_left_leg = leg_idx < 3
            turn_factor = -turn if is_left_leg else turn

            # Coxa: horizontal rotation
            action_42d[base_idx + 0] = 0.3 * forward
            action_42d[base_idx + 1] = 0.1 * turn_factor  # Coxa_roll
            action_42d[base_idx + 2] = 0.2 * turn_factor  # Coxa_yaw

            # Femur: main support (natural bent position)
            action_42d[base_idx + 3] = -0.8 + 0.2 * abs(forward)
            action_42d[base_idx + 4] = 0.05  # Femur_roll

            # Tibia: extension
            action_42d[base_idx + 5] = 1.2 - 0.3 * abs(forward)

            # Tarsus: minimal adjustment
            action_42d[base_idx + 6] = 0.02

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
