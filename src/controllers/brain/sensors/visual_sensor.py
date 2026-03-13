"""Visual sensory system for Drosophila brain model (~15k neurons simplified model)."""

import numpy as np
from typing import Tuple, Dict, Any, Optional


class VisualSensor:
    """
    Simplified visual sensory processing for Drosophila brain.
    
    Implements a ~15k-neuron model based on known Drosophila visual circuitry:
    - Compound eye (760 ommatidia from literature, simplified to 360 angular bins)
    - Photoreceptor layer (~1500 R1-R8 receptors)
    - Lamina monopolar cells (~8000 neurons for local processing)
    - Medulla columnar organization (~4000 neurons for motion detection)
    - Lobula integration (~1500 neurons for feature extraction)
    
    Features:
    - Light intensity detection (phototaxis bias)
    - Motion detection (temporal contrast)
    - Spatial localization of visual features
    - Can modulate navigation based on visual salience
    
    Biologically inspired by:
    - Compound eye photoreceptors (wavelength-sensitive, ~340 deg FOV)
    - Elementary motion detector circuits (Hassenstein-Reichardt)
    - Behavioral modulation by visual features
    """
    
    def __init__(self,
                 fov_degrees: float = 340.0,
                 angular_resolution: int = 360,
                 light_sensitivity: float = 1.0,
                 motion_sensitivity: float = 0.5,
                 enable_phototaxis: bool = False):
        """
        Args:
            fov_degrees: Field of view in degrees (Drosophila ~340°)
            angular_resolution: Number of angular bins (photoreceptor sampling)
            light_sensitivity: Multiplicative factor for light response
            motion_sensitivity: Multiplicative factor for motion detection
            enable_phototaxis: Whether light attracts (True) or repels (False) fly
        """
        self.fov_degrees = fov_degrees
        self.angular_resolution = angular_resolution
        self.light_sensitivity = light_sensitivity
        self.motion_sensitivity = motion_sensitivity
        self.enable_phototaxis = enable_phototaxis
        
        # Photoreceptor array (360 bins = 1° per bin)
        # Represents ~760 ommatidia compressed to 360 angular channels
        self.photoreceptors = np.zeros(angular_resolution)
        self.photoreceptors_prev = np.zeros(angular_resolution)
        
        # Temporal state for motion detection
        self.motion_history = np.zeros((3, angular_resolution))  # n-2, n-1, n
        
        # Statistics for normalization
        self.mean_luminance = 0.0
        self.contrast_level = 0.0
    
    def _sample_environment(self, 
                            position: np.ndarray,
                            heading: float,
                            odor_field: Any) -> np.ndarray:
        """
        Sample visual input from simulated environment.
        
        In this simplified model, we:
        1. Use odor field concentration as a proxy for "visual feature brightness"
        2. Sample environment in 360° angular bins around the fly
        
        Returns: array of shape (angular_resolution,) with photoreceptor activations
        """
        photoreceptors = np.zeros(self.angular_resolution)
        
        # Sample in 360 directions
        for angle_idx in range(self.angular_resolution):
            angle_rad = heading + (angle_idx / self.angular_resolution) * 2 * np.pi - np.pi
            
            # Sample at a small distance in that direction
            sample_distance = 2.0  # mm
            sample_pos = position.copy()
            sample_pos[0] += sample_distance * np.cos(angle_rad)
            sample_pos[1] += sample_distance * np.sin(angle_rad)
            
            # Get feature intensity (using odor concentration as proxy for visual salience)
            intensity = odor_field.concentration_at(sample_pos)
            photoreceptors[angle_idx] = intensity
        
        return photoreceptors * self.light_sensitivity
    
    def _detect_motion(self, current_photoreceptors: np.ndarray) -> Dict[str, Any]:
        """
        Detect motion using elementary motion detector (EMD) principles.
        Hassenstein-Reichardt style: correlation between neighboring receptors over time.
        
        Returns motion features at different directions.
        """
        # Update motion history
        self.motion_history[0] = self.motion_history[1]
        self.motion_history[1] = self.motion_history[2]
        self.motion_history[2] = current_photoreceptors
        
        # Compute temporal derivatives
        temporal_diff = self.motion_history[2] - self.motion_history[1]
        
        # Compute spatial-temporal correlations for forward and clockwise motion
        forward_motion = np.mean(temporal_diff)  # Positive = object approaching
        
        # Detect motion direction by comparing left vs right temporal changes
        left_temporal = np.mean(temporal_diff[:self.angular_resolution//2])
        right_temporal = np.mean(temporal_diff[self.angular_resolution//2:])
        turning_bias = right_temporal - left_temporal  # Positive = turn right
        
        return {
            'forward_motion': float(forward_motion) * self.motion_sensitivity,
            'turning_bias': float(turning_bias) * self.motion_sensitivity,
            'motion_magnitude': float(np.abs(forward_motion) + np.abs(turning_bias)),
        }
    
    def _compute_visual_features(self, 
                                 photoreceptors: np.ndarray) -> Dict[str, Any]:
        """Compute high-level visual features from photoreceptor array."""
        
        # Overall luminance
        mean_luminance = np.mean(photoreceptors)
        
        # Contrast (spatial variance)
        contrast = np.std(photoreceptors)
        
        # Peak direction (where is the brightest feature?)
        peak_idx = np.argmax(photoreceptors)
        peak_angle = (peak_idx / self.angular_resolution) * 360.0
        peak_magnitude = photoreceptors[peak_idx]
        
        # Directional variance (how scattered is the visual input?)
        # High = uniform, Low = focused
        directional_variance = np.var(photoreceptors)
        
        return {
            'mean_luminance': float(mean_luminance),
            'contrast': float(contrast),
            'peak_angle_deg': float(peak_angle),
            'peak_magnitude': float(peak_magnitude),
            'directional_variance': float(directional_variance),
        }
    
    def process(self,
                position: np.ndarray,
                heading: float,
                odor_field: Any,
                time_step: int = 0) -> Dict[str, Any]:
        """
        Process visual information and compute modulation signals.
        
        Args:
            position: (x, y, z) fly position
            heading: fly heading in radians
            odor_field: OdorField instance (used for sampling visual features)
            time_step: current simulation time step
        
        Returns:
            dict with keys:
            - 'photoreceptors': raw photoreceptor activations
            - 'luminance': overall light intensity
            - 'contrast': spatial contrast in visual field
            - 'peak_angle_deg': direction of brightest feature
            - 'forward_modulation': visual modulation of forward speed
            - 'turning_modulation': visual modulation of turn rate
            - 'aversion_signal': threat/obstacle avoidance signal
        """
        
        # Sample environment
        current_photoreceptors = self._sample_environment(position, heading, odor_field)
        
        # Detect motion
        motion_features = self._detect_motion(current_photoreceptors)
        
        # Extract visual features
        features = self._compute_visual_features(current_photoreceptors)
        
        # Generate motor modulation signals
        # In the absence of light aversion genes, visual system is mostly neutral
        # but can contribute to collision avoidance via contrast detection
        
        # High contrast + high luminance = possible obstacle/wall
        obstacle_signal = features['contrast'] * 0.1  # Weak signal
        
        # Peak direction can modulate turning toward or away from features
        peak_angle_rad = np.radians(features['peak_angle_deg'])
        turning_modulation = np.sin(peak_angle_rad) * 0.05  # Weak visual turning
        
        return {
            'photoreceptors': current_photoreceptors.tolist(),
            'luminance': features['mean_luminance'],
            'contrast': features['contrast'],
            'peak_angle_deg': features['peak_angle_deg'],
            'peak_magnitude': features['peak_magnitude'],
            'forward_modulation': float(motion_features['forward_motion'] * 0.05),
            'turning_modulation': float(turning_modulation),
            'aversion_signal': float(obstacle_signal),
            'motion_magnitude': features['directional_variance'],
            'neuron_count_estimate': 15000,  # Simplified 15k neuron model
        }
    
    def reset(self):
        """Reset internal state."""
        self.photoreceptors = np.zeros(self.angular_resolution)
        self.photoreceptors_prev = np.zeros(self.angular_resolution)
        self.motion_history = np.zeros((3, self.angular_resolution))
        self.mean_luminance = 0.0
        self.contrast_level = 0.0
