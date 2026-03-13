"""Olfactory sensory system for Drosophila brain model."""

import numpy as np
from typing import Tuple, Dict, Any


class OlfactorySensor:
    """
    Olfactory sensory processing based on bilateral comparison.
    
    Implements:
    - Left/center/right concentration sampling
    - Bilateral gradient computation
    - Temporal concentration change detection
    - Plateau detection for goal-reaching behavior
    
    Biologically inspired by:
    - Antennal receptors (Or-types: Or10a, Or47a, etc.)
    - Antennal lobe (glomeruli-based processing)
    - Mushroom body (Kenyon cells for decision integration)
    """
    
    def __init__(self, 
                 sampling_interval: float = 0.02,
                 turn_factor: float = 5.0,
                 plateau_threshold: float = 88.0,
                 plateau_steps_required: int = 10):
        """
        Args:
            sampling_interval: radians, angle between left/center/right samples
            turn_factor: multiplicative factor for gradient-based turning
            plateau_threshold: concentration level indicating goal proximity
            plateau_steps_required: steps without improvement to declare plateau
        """
        self.sampling_interval = sampling_interval
        self.turn_factor = turn_factor
        self.plateau_threshold = plateau_threshold
        self.plateau_steps_required = plateau_steps_required
        
        # State tracking
        self.prev_concentration = None
        self.steps_without_improvement = 0
        self.in_plateau = False
        self.at_goal = False
    
    def process(self,
                odor_field: Any,
                position: np.ndarray,
                heading: float,
                concentration_center: float) -> Dict[str, Any]:
        """
        Process olfactory input and compute motor signals.
        
        Args:
            odor_field: OdorField instance
            position: (x, y, z) fly position
            heading: fly heading in radians
            concentration_center: concentration at fly position
        
        Returns:
            dict with keys:
            - 'samples': dict with 'left', 'center', 'right' concentrations
            - 'gradient': bilateral gradient strength
            - 'conc_change': concentration change since last step
            - 'forward_cmd': forward motor command [0, 1]
            - 'turn_cmd': turn motor command [-1, 1]
            - 'plateau_active': boolean indicating plateau detection
            - 'at_goal': boolean indicating goal reached
        """
        
        # Sample left/center/right
        left_pos = position.copy()
        left_pos[0] += self.sampling_interval * np.cos(heading + np.pi/2)
        left_pos[1] += self.sampling_interval * np.sin(heading + np.pi/2)
        
        right_pos = position.copy()
        right_pos[0] += self.sampling_interval * np.cos(heading - np.pi/2)
        right_pos[1] += self.sampling_interval * np.sin(heading - np.pi/2)
        
        conc_left = odor_field.concentration_at(left_pos)
        conc_right = odor_field.concentration_at(right_pos)
        
        samples = {
            'left': float(conc_left),
            'center': float(concentration_center),
            'right': float(conc_right),
        }
        
        # Bilateral gradient
        gradient = conc_left - conc_right
        
        # Concentration change tracking
        if self.prev_concentration is None:
            conc_change = 0.0
        else:
            conc_change = concentration_center - self.prev_concentration
        
        self.prev_concentration = concentration_center
        
        # Plateau detection: no improvement + high concentration
        if conc_change > 0.0:
            self.steps_without_improvement = 0
        else:
            self.steps_without_improvement += 1
        
        # Check plateau: high concentration AND steps without improvement
        self.in_plateau = (
            concentration_center > self.plateau_threshold and
            self.steps_without_improvement >= self.plateau_steps_required
        )
        
        # Motor commands based on gradient and plateau
        if self.in_plateau:
            forward_cmd = 0.0
            turn_cmd = 0.0
            self.at_goal = True
        else:
            forward_cmd = 0.9
            turn_cmd = gradient * self.turn_factor
            turn_cmd = np.clip(turn_cmd, -1.0, 1.0)
        
        return {
            'samples': samples,
            'gradient': float(gradient),
            'conc_change': float(conc_change),
            'forward_cmd': float(forward_cmd),
            'turn_cmd': float(turn_cmd),
            'plateau_active': self.in_plateau,
            'at_goal': self.at_goal,
            'steps_without_improvement': self.steps_without_improvement,
        }
    
    def reset(self):
        """Reset internal state."""
        self.prev_concentration = None
        self.steps_without_improvement = 0
        self.in_plateau = False
        self.at_goal = False
