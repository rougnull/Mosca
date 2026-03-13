"""Mechanoreceptor sensory system for obstacle/wall detection."""

import numpy as np
from typing import Tuple, Dict, Any, List


class MechanoreceptorSensor:
    """
    Mechanoreceptor system for detecting obstacles and walls.
    
    Implements:
    - Touch-sensitive neurons (trichoid sensilla)
    - Wall proximity detection
    - Directional information from bilateral antennae
    
    Biologically based on:
    - Drosophila larva nociceptors (class IV neurons sensitive to physical contact)
    - Adult antennal mechanoreceptors
    - Wall-sensitive neurons in the fly brain
    """
    
    def __init__(self,
                 sensing_distance: float = 3.0,
                 bilateral_span: float = 0.05):
        """
        Args:
            sensing_distance: maximum distance to detect walls (mm)
            bilateral_span: angle between left and right antennae (radians)
        """
        self.sensing_distance = sensing_distance
        self.bilateral_span = bilateral_span
    
    def process(self,
                wall_proximity_mm: float,
                wall_offset_angle: float) -> Dict[str, Any]:
        """
        Process mechanoreceptor input from walls.
        
        Args:
            wall_proximity_mm: distance to nearest wall (mm), or 999 if none
            wall_offset_angle: angle offset to wall from body axis
                             -1 = left, 0 = front, 1 = right
        
        Returns:
            dict with keys:
            - 'proximity': normalized proximity signal [0, 1]
            - 'wall_detected': boolean
            - 'direction_preference': turning command based on wall position
            - 'avoidance_strength': strength of avoidance response
        """
        
        # Detect if wall is within sensing distance
        wall_detected = wall_proximity_mm < self.sensing_distance
        
        # Normalize proximity to [0, 1]
        if wall_detected:
            proximity = 1.0 - (wall_proximity_mm / self.sensing_distance)
            proximity = np.clip(proximity, 0.0, 1.0)
        else:
            proximity = 0.0
        
        # Generate avoidance response based on wall direction
        # If wall is on left (-1), turn right (positive turn command)
        # If wall is on right (1), turn left (negative turn command)
        direction_preference = -wall_offset_angle * proximity  # Negative coupling
        
        # Avoidance strength scales with proximity
        avoidance_strength = proximity * 0.3  # Max 0.3 contribution to motor commands
        
        return {
            'proximity': float(proximity),
            'wall_detected': bool(wall_detected),
            'wall_direction': float(wall_offset_angle),
            'direction_preference': float(direction_preference),
            'avoidance_strength': float(avoidance_strength),
            'sensing_distance_mm': float(self.sensing_distance),
        }
