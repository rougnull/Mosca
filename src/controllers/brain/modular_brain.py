"""
Modular Drosophila brain with integrated sensory processing.

ARQUITECTURA DE INTEGRACIÓN SENSORIAL:
======================================

En lugar de decisiones independientes que se superponen, implementamos un sistema
de "command fusion" donde:

1. OLFATO (controlador principal):
   - Detecta gradiente bilateral → dirección de giro
   - Detecta cambio temporal → velocidad forward
   - Genera comando base: (forward, turn)

2. VISUAL (modulador de confianza):
   - Analiza luminancia, contraste, movimiento
   - Genera "confidence score" [0,1] sobre la decisión actual
   - Si ve obstáculo/pared: confidence baja
   - Si ambiente claro: confidence alta
   - Modula amplitud de los comandos (forward *= confidence)

3. MECANORECEPTORES (filtro de restricciones):
   - Detecta paredes/obstáculos en la trayectoria actual
   - Bloquea/modifica giros que irían hacia la pared
   - Reduce forward si hay contacto inminente
   - NUNCA permite que la mosca atraviese paredes

FLUJO:
   Olfato → (forward_base, turn_base)
   ↓
   Visual evalúa situación → confidence [0,1]
   ↓
   Mecano verifica paredes → válido? sí/no
   ↓
   Comando final = (forward_base * confidence * pared_factor, turn_modificado)

Esto asegura que cada sensor contribuye de forma coherente, no sumadera de voces.
"""

import numpy as np
from typing import Optional, Tuple, Dict, Any

from .sensors.olfactory_sensor import OlfactorySensor
from .sensors.visual_sensor import VisualSensor
from .sensors.mechanoreceptor_sensor import MechanoreceptorSensor


class ModularBrain:
    """
    Modular Drosophila brain with true sensory integration.
    
    Implements command fusion: olfaction proposes, vision evaluates confidence,
    mechanoreceptors enforce constraints.
    """
    
    def __init__(self,
                 bilateral_distance: float = 1.2,
                 forward_scale: float = 1.0,
                 turn_scale: float = 0.8):
        """
        Initialize modular brain with integrated sensory processing.
        
        Args:
            bilateral_distance: distance between olfactory sampling points (mm)
            forward_scale: scaling factor for forward motor commands
            turn_scale: scaling factor for turning motor commands
        """
        self.bilateral_distance = bilateral_distance
        self.forward_scale = forward_scale
        self.turn_scale = turn_scale
        
        # Sensory modules
        self.olfactory = OlfactorySensor(
            sampling_interval=bilateral_distance,
            turn_factor=turn_scale * 5.0,
            plateau_threshold=88.0,
            plateau_steps_required=10
        )
        
        self.visual = VisualSensor(
            fov_degrees=340.0,
            angular_resolution=360,
            light_sensitivity=1.0,
            motion_sensitivity=0.5,
            enable_phototaxis=False
        )
        
        self.mechanoreceptor = MechanoreceptorSensor(
            sensing_distance=3.0,
            bilateral_span=0.05
        )
        
        # Integration state
        self._debug_step_count = 0
        self._prev_visual_confidence = 1.0
    
    def _compute_visual_confidence(self, 
                                   visual_output: Dict[str, Any],
                                   wall_proximity_mm: float) -> float:
        """
        Compute how confident the visual system is about the current action.
        
        Returns confidence score [0, 1]:
        - 1.0: clear environment, no threats
        - 0.8-0.9: normal navigation
        - 0.5-0.7: visual uncertainty (high contrast, movement)
        - 0.2-0.4: wall/obstacle detected
        - 0.0: collision imminent
        
        Args:
            visual_output: output from VisualSensor.process()
            wall_proximity_mm: distance to nearest wall
        
        Returns:
            confidence [0, 1]
        """
        # Base confidence from luminance/contrast
        luminance = max(0.1, visual_output['luminance'])  # Avoid division by zero
        contrast = visual_output['contrast']
        
        # High contrast = uncertainty (might be obstacle)
        # Low contrast = clarity
        contrast_penalty = min(0.5, contrast / 100.0)  # Max 50% penalty
        
        # Luminance provides some confidence
        # Very bright or very dark = less confidence
        luminance_confidence = 1.0 - np.abs(luminance - 50.0) / 100.0
        luminance_confidence = np.clip(luminance_confidence, 0.3, 1.0)
        
        # Start with luminance-based confidence
        confidence = luminance_confidence * (1.0 - contrast_penalty)
        
        # WALL PROXIMITY: Most important for command fusion
        # If wall is nearby, confidence in the current forward/turn action is LOW
        if wall_proximity_mm < 3.0:
            # Wall detected
            # Very close (< 0.5mm): confidence near zero
            # At 3mm: moderate reduction
            wall_penalty = 1.0 - min(1.0, (3.0 - wall_proximity_mm) / 3.0)
            wall_penalty = max(0.1, wall_penalty)  # Minimum confidence 10%
            confidence = confidence * wall_penalty
        
        # MOTION DETECTION: High motion = lower confidence
        motion_magnitude = visual_output['motion_magnitude']
        if motion_magnitude > 10.0:  # High motion
            confidence = confidence * 0.7  # 30% reduction
        
        return np.clip(confidence, 0.0, 1.0)
    
    def _modify_turn_for_obstacles(self,
                                   turn_cmd: float,
                                   wall_offset_angle: float,
                                   wall_proximity_mm: float,
                                   mechanoreceptor_output: Dict[str, Any]) -> float:
        """
        Modify turning command to avoid obstacles.
        
        If there's a wall on the left, don't allow large positive (left) turns.
        If there's a wall on the right, don't allow large negative (right) turns.
        
        Args:
            turn_cmd: desired turning from olfaction [-1, 1]
            wall_offset_angle: direction of wall [-1=left, 0=front, 1=right]
            wall_proximity_mm: distance to wall
            mechanoreceptor_output: mechanoreceptor sensor output
        
        Returns:
            modified turn command
        """
        if not mechanoreceptor_output['wall_detected']:
            return turn_cmd  # No walls, use original turn
        
        proximity = mechanoreceptor_output['proximity']  # [0, 1]
        
        # Wall direction: negative = wall on left, positive = wall on right
        wall_side = wall_offset_angle  # -1.0 to 1.0
        
        # If we want to turn TOWARD the wall, cancel it
        # turn_cmd > 0 = turn left
        # wall_side < 0 = wall on left
        # Both positive = turning toward wall (BAD)
        
        turn_by_direction_penalty = abs(turn_cmd * wall_side)
        
        # Scale penalty by proximity: closer wall = stronger penalty
        if proximity > 0.5:
            # Close to wall: aggressive penalty
            if turn_cmd * wall_side > 0:  # Trying to turn toward wall
                turn_cmd = turn_cmd * (1.0 - proximity)  # Reduce turn
        
        return np.clip(turn_cmd, -1.0, 1.0)
    
    def _reduce_forward_near_obstacles(self,
                                       forward_cmd: float,
                                       mechanoreceptor_output: Dict[str, Any]) -> float:
        """
        Reduce forward speed if wall is ahead or very close.
        
        Args:
            forward_cmd: desired forward from olfaction [0, 1]
            mechanoreceptor_output: mechanoreceptor sensor output
        
        Returns:
            modified forward command
        """
        if not mechanoreceptor_output['wall_detected']:
            return forward_cmd
        
        proximity = mechanoreceptor_output['proximity']  # [0, 1]
        wall_direction = mechanoreceptor_output['wall_direction']  # -1 to 1
        
        # CRITICAL FIX: wall_direction is calculated from WALL ORIENTATION not from direction to wall point
        # For perpendicular wall (like x=40 vertical), wall_direction = -1 or 1 (not 0)
        # So we need INVERSE logic: only penalize when wall_direction is NEAR 0 (parallel wall ahead)
        
        # When wall is perpendicular (|wall_direction| > 0.5), fly can navigate along it
        # Only stop if wall is truly BLOCKING path (parallel wall ahead)
        if abs(wall_direction) < 0.5 and proximity > 0.5:
            # Wall is roughly ahead and very close: gentle penalty
            penalty = max(0.5, 1.0 - proximity * 0.3)  # Softer: min 50%, gentle curve
            forward_cmd = forward_cmd * penalty
        # If |wall_direction| >= 0.5, wall is perpendicular (to the side) - allow navigation
        
        return np.clip(forward_cmd, 0.0, 1.0)
    
    def step(self,
             odor_field,
             current_position: np.ndarray,
             heading_radians: float,
             wall_proximity_mm: float = 999.0,
             wall_offset_angle: float = 0.0) -> np.ndarray:
        """
        Execute one step of integrated sensory decision-making.
        
        PROCESS:
        1. Olfaction computes base commands (forward, turn)
        2. Vision evaluates confidence in these commands
        3. Mechanoreceptors check for obstacles
        4. Final command = base * (visual_confidence) * (obstacle_constraints)
        
        Args:
            odor_field: OdorField instance
            current_position: (x, y, z) fly position
            heading_radians: fly heading in radians
            wall_proximity_mm: distance to nearest wall (mm)
            wall_offset_angle: wall direction [-1=left, 0=front, 1=right]
        
        Returns:
            np.ndarray: [forward, turn] motor command
        """
        self._debug_step_count += 1
        
        # STEP 1: OLFACTION (primary controller)
        concentration = float(odor_field.concentration_at(current_position))
        olfactory_output = self.olfactory.process(
            odor_field, current_position, heading_radians, concentration
        )
        forward_base = olfactory_output['forward_cmd']
        turn_base = olfactory_output['turn_cmd']
        
        # STEP 2: VISION (confidence evaluation)
        visual_output = self.visual.process(
            current_position, heading_radians, odor_field, self._debug_step_count
        )
        visual_confidence = self._compute_visual_confidence(visual_output, wall_proximity_mm)
        
        # STEP 3: MECHANORECEPTORS (constraint enforcement)
        mechanoreceptor_output = self.mechanoreceptor.process(
            wall_proximity_mm, wall_offset_angle
        )
        
        # STEP 4: COMMAND FUSION
        # Forward: base command × visual confidence × obstacle factor
        forward = forward_base * visual_confidence
        forward = self._reduce_forward_near_obstacles(forward, mechanoreceptor_output)
        
        # Turn: base command modified by obstacle avoidance
        # Visual doesn't directly modify turn, but obstacles do
        turn = turn_base
        turn = self._modify_turn_for_obstacles(turn, wall_offset_angle, wall_proximity_mm, mechanoreceptor_output)
        
        # If wall very close and ahead, add active avoidance turn
        if mechanoreceptor_output['wall_detected'] and mechanoreceptor_output['proximity'] > 0.7:
            # Turn strongly AWAY from wall
            avoidance_turn = -wall_offset_angle * 0.5  # Strong turning away
            turn = turn + avoidance_turn
            turn = np.clip(turn, -1.0, 1.0)
        
        # Final clipping
        forward = np.clip(forward, 0.0, 1.0)
        turn = np.clip(turn, -1.0, 1.0)
        
        # Debug output
        if self._debug_step_count <= 5:
            print(f"\n[Modular Brain Step {self._debug_step_count}]")
            print(f"  Position: {current_position}")
            print(f"  Concentration: {concentration:.2f}")
            print(f"  Olfaction: fwd={forward_base:.3f}, turn={turn_base:.3f}")
            print(f"  Visual confidence: {visual_confidence:.3f}")
            if mechanoreceptor_output['wall_detected']:
                print(f"  Obstacle: proximity={wall_proximity_mm:.2f}mm, direction={wall_offset_angle:.2f}")
            print(f"  FINAL: forward={forward:.3f}, turn={turn:.3f}")
        
        return np.array([forward, turn])
    
    def reset(self):
        """Reset all internal state."""
        self.olfactory.reset()
        self.visual.reset()
        self._debug_step_count = 0
        self._prev_visual_confidence = 1.0
    
    def get_diagnostics(self) -> dict:
        """Get diagnostic information from all sensory systems."""
        return {
            "olfactory": {
                "plateau_active": self.olfactory.in_plateau,
                "at_goal": self.olfactory.at_goal,
                "steps_without_improvement": self.olfactory.steps_without_improvement,
            },
            "visual": {
                "neuron_count_estimate": 15000,
            },
            "mechanoreceptor": {
                "enabled": True,
            }
        }

