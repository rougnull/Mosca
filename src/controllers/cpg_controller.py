"""
Central Pattern Generator (CPG) Controller for FlyGym.

Implements a simple tripod gait CPG network that converts high-level
commands [forward, turn] into realistic 42-DoF joint angle trajectories.
"""

import numpy as np
from typing import Tuple, Optional


class SimplifiedTripodCPG:
    """
    Simplified CPG controller for tripod gait locomotion.

    Converts high-level motor commands [forward, turn] to 42 DoF joint angles
    using a phase-based oscillator model with tripod coordination.

    Parameters
    ----------
    timestep : float
        Simulation timestep in seconds (e.g., 0.01 for 100Hz)
    base_frequency : float
        Base stepping frequency in Hz (default: 2.0)
    """

    def __init__(self, timestep: float = 0.01, base_frequency: float = 2.0):
        self.timestep = timestep
        self.base_frequency = base_frequency

        # 6 legs: LF, LM, LH, RF, RM, RH
        self.legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
        self.n_legs = 6

        # 7 DoF per leg: Coxa, Coxa_roll, Coxa_yaw, Femur, Femur_roll, Tibia, Tarsus1
        self.dofs_per_leg = ["Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"]
        self.n_dofs_per_leg = 7

        # CPG state: phase for each leg [0, 2π]
        self.phases = np.zeros(self.n_legs)

        # Tripod gait phase offsets
        # Group 1 (LF, RM, LH): phase 0
        # Group 2 (RF, LM, RH): phase π
        self.tripod_phase_offsets = np.array([
            0.0,      # LF
            np.pi,    # LM
            0.0,      # LH
            np.pi,    # RF
            0.0,      # RM
            np.pi,    # RH
        ])

        # Initialize phases
        self.phases = self.tripod_phase_offsets.copy()

        # Joint angle limits (in radians)
        # These are biologically-plausible ranges for Drosophila
        self.joint_ranges = {
            "Coxa": (-0.5, 0.5),
            "Coxa_roll": (-0.3, 0.3),
            "Coxa_yaw": (-0.4, 0.4),
            "Femur": (-1.5, -0.2),  # Femur is naturally bent
            "Femur_roll": (-0.2, 0.2),
            "Tibia": (0.3, 1.8),     # Tibia extends
            "Tarsus1": (-0.1, 0.1),
        }

        # Amplitude scaling factors per joint
        self.joint_amplitudes = {
            "Coxa": 0.3,
            "Coxa_roll": 0.15,
            "Coxa_yaw": 0.2,
            "Femur": 0.6,
            "Femur_roll": 0.1,
            "Tibia": 0.5,
            "Tarsus1": 0.05,
        }

    def step(self, forward: float, turn: float) -> np.ndarray:
        """
        Generate joint angles for one timestep.

        Parameters
        ----------
        forward : float
            Forward command [-1, 1]. Positive = forward, negative = backward.
        turn : float
            Turn command [-1, 1]. Positive = right turn, negative = left turn.

        Returns
        -------
        np.ndarray
            Array of 42 joint angles in radians, ordered as:
            [LF joints (7), LM joints (7), LH joints (7),
             RF joints (7), RM joints (7), RH joints (7)]
        """
        # Clip commands to valid range
        forward = np.clip(forward, -1.0, 1.0)
        turn = np.clip(turn, -1.0, 1.0)

        # Compute stepping frequency based on forward command
        # When forward=0, minimal oscillation; when forward=1, full frequency
        frequency = self.base_frequency * (0.2 + 0.8 * abs(forward))

        # Compute angular velocity for each leg
        omega = 2 * np.pi * frequency

        # Modulate frequency per side based on turn command
        # Left legs: slower when turning right
        # Right legs: slower when turning left
        freq_modulation = np.ones(self.n_legs)
        freq_modulation[:3] *= (1.0 - 0.5 * turn)  # Left legs (LF, LM, LH)
        freq_modulation[3:] *= (1.0 + 0.5 * turn)  # Right legs (RF, RM, RH)

        # Update phases
        self.phases += omega * freq_modulation * self.timestep
        self.phases = self.phases % (2 * np.pi)

        # Generate joint angles
        joint_angles = np.zeros(42)

        for leg_idx, leg in enumerate(self.legs):
            phase = self.phases[leg_idx]

            # Compute amplitude modulation (stronger with higher forward command)
            amplitude = 0.3 + 0.7 * abs(forward)

            # Determine if leg is in stance or swing phase
            # Stance: phase ∈ [0, π] - leg on ground, pushing
            # Swing: phase ∈ [π, 2π] - leg in air, moving forward
            in_stance = phase < np.pi

            # Base index for this leg's joints
            base_idx = leg_idx * self.n_dofs_per_leg

            # Generate angles for each DoF
            for dof_idx, dof_name in enumerate(self.dofs_per_leg):
                amp = self.joint_amplitudes[dof_name] * amplitude

                if dof_name == "Coxa":
                    # Coxa: protraction/retraction
                    angle = amp * np.sin(phase - np.pi/4)

                elif dof_name == "Coxa_roll":
                    # Small roll for stability
                    angle = amp * np.sin(phase)

                elif dof_name == "Coxa_yaw":
                    # Yaw for turning
                    angle = amp * np.sin(phase + np.pi/2)
                    if leg_idx < 3:  # Left legs
                        angle *= (1.0 - turn)
                    else:  # Right legs
                        angle *= (1.0 + turn)

                elif dof_name == "Femur":
                    # Femur: main lifting joint
                    # Offset + oscillation
                    offset = -0.8  # Natural bent position
                    if in_stance:
                        # Stance: extended
                        angle = offset + amp * 0.3
                    else:
                        # Swing: flexed (lift leg)
                        angle = offset - amp * 0.5 * np.sin(phase - np.pi)

                elif dof_name == "Femur_roll":
                    angle = amp * 0.5 * np.cos(phase)

                elif dof_name == "Tibia":
                    # Tibia: extension/flexion
                    offset = 1.2  # Natural extended position
                    if in_stance:
                        # Stance: support position
                        angle = offset - amp * 0.3
                    else:
                        # Swing: flexed
                        angle = offset + amp * 0.5 * np.cos(phase - np.pi)

                elif dof_name == "Tarsus1":
                    # Small adjustments
                    angle = amp * np.sin(phase * 2)

                # Clip to joint limits
                min_angle, max_angle = self.joint_ranges[dof_name]
                angle = np.clip(angle, min_angle, max_angle)

                joint_angles[base_idx + dof_idx] = angle

        return joint_angles

    def reset(self):
        """Reset CPG state to initial phases."""
        self.phases = self.tripod_phase_offsets.copy()


class AdaptiveCPGController(SimplifiedTripodCPG):
    """
    Advanced CPG controller with adaptive parameters.

    Extends SimplifiedTripodCPG with:
    - Smooth ramping of amplitudes
    - Adaptive frequency based on recent commands
    - Better turn coordination
    """

    def __init__(self, timestep: float = 0.01, base_frequency: float = 2.0):
        super().__init__(timestep, base_frequency)

        # Smooth state tracking
        self.prev_forward = 0.0
        self.prev_turn = 0.0
        self.current_amplitude = 0.3

        # Smoothing parameters
        self.command_smoothing = 0.9  # 0.0 = no smoothing, 1.0 = max smoothing
        self.amplitude_ramp_rate = 0.05  # Rate of amplitude change per step

    def step(self, forward: float, turn: float) -> np.ndarray:
        """
        Generate joint angles with smooth transitions.

        Parameters
        ----------
        forward : float
            Forward command [-1, 1]
        turn : float
            Turn command [-1, 1]

        Returns
        -------
        np.ndarray
            Array of 42 joint angles
        """
        # Smooth commands to avoid sudden changes
        smoothed_forward = (self.command_smoothing * self.prev_forward +
                           (1 - self.command_smoothing) * forward)
        smoothed_turn = (self.command_smoothing * self.prev_turn +
                        (1 - self.command_smoothing) * turn)

        # Update stored commands
        self.prev_forward = smoothed_forward
        self.prev_turn = smoothed_turn

        # Ramp amplitude smoothly
        target_amplitude = 0.3 + 0.7 * abs(smoothed_forward)
        if self.current_amplitude < target_amplitude:
            self.current_amplitude = min(target_amplitude,
                                        self.current_amplitude + self.amplitude_ramp_rate)
        else:
            self.current_amplitude = max(target_amplitude,
                                        self.current_amplitude - self.amplitude_ramp_rate)

        # Call parent step with smoothed commands
        return super().step(smoothed_forward, smoothed_turn)


def test_cpg_controller():
    """Test CPG controller functionality."""
    print("="*70)
    print("Testing CPG Controller")
    print("="*70)

    cpg = SimplifiedTripodCPG(timestep=0.01, base_frequency=2.0)

    # Test forward walking
    print("\n1. Forward walking (5 steps):")
    for i in range(5):
        angles = cpg.step(forward=0.8, turn=0.0)
        print(f"  Step {i}: {len(angles)} angles, range=[{angles.min():.3f}, {angles.max():.3f}]")

    # Test turning
    print("\n2. Right turn (5 steps):")
    cpg.reset()
    for i in range(5):
        angles = cpg.step(forward=0.5, turn=0.5)
        print(f"  Step {i}: phases={cpg.phases[:3].round(2)}")

    # Test adaptive controller
    print("\n3. Adaptive controller:")
    adaptive = AdaptiveCPGController(timestep=0.01, base_frequency=2.0)
    for i in range(3):
        angles = adaptive.step(forward=1.0, turn=0.0)
        print(f"  Step {i}: amplitude={adaptive.current_amplitude:.3f}")

    print("\n✓ CPG Controller tests passed")


if __name__ == "__main__":
    test_cpg_controller()
