#!/usr/bin/env python3
"""
Test brain in isolation without FlyGym physics.

This script tests the ImprovedOlfactoryBrain independently to verify
it generates correct motor signals before integrating with physics.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from olfaction.odor_field import OdorField


def test_brain_isolated():
    """Test brain with simulated trajectory."""
    print("="*70)
    print("BRAIN ISOLATED TEST")
    print("="*70)

    # Create brain
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8,
        temporal_gradient_gain=10.0
    )

    # Create odor field (matching simulation)
    odor_field = OdorField(
        sources=(50, 50, 5),  # Source location
        sigma=8.0,
        amplitude=100.0
    )

    print(f"\nOdor source: (50, 50, 5)")
    print(f"Odor sigma: 8.0mm")
    print(f"Odor amplitude: 100.0")

    # Simulate fly trajectory (starting from simulation data)
    positions = [
        np.array([35.015, 35.007, 1.783]),  # Step 0
        np.array([35.014, 35.007, 1.785]),  # Step 1
        np.array([35.012, 35.006, 1.788]),  # Step 2
        np.array([35.010, 35.005, 1.792]),  # Step 3
        np.array([35.007, 35.004, 1.796]),  # Step 4
    ]

    headings = [
        0.837,  # ~48°
        0.837,
        0.838,
        0.840,
        0.842,
    ]

    print("\n" + "="*70)
    print("TESTING BRAIN WITH TRAJECTORY")
    print("="*70)

    for i, (pos, heading) in enumerate(zip(positions, headings)):
        print(f"\n--- Step {i} ---")
        print(f"Position: [{pos[0]:.6f}, {pos[1]:.6f}, {pos[2]:.6f}]")
        print(f"Heading: {heading:.6f} rad ({np.degrees(heading):.2f}°)")

        # Get odor concentrations
        conc_center = odor_field.concentration_at(pos)

        # Calculate bilateral positions
        left_angle = heading + np.pi / 2
        right_angle = heading - np.pi / 2

        left_pos = pos + 1.2 * np.array([np.cos(left_angle), np.sin(left_angle), 0])
        right_pos = pos + 1.2 * np.array([np.cos(right_angle), np.sin(right_angle), 0])

        conc_left = odor_field.concentration_at(left_pos)
        conc_right = odor_field.concentration_at(right_pos)

        print(f"Conc center: {conc_center:.6f}")
        print(f"Conc left: {conc_left:.6f}")
        print(f"Conc right: {conc_right:.6f}")
        print(f"Gradient (L-R): {conc_left - conc_right:.6f}")

        # Call brain
        motor_signal = brain.step(odor_field, pos, heading)

        print(f">>> Motor signal: forward={motor_signal[0]:.6f}, turn={motor_signal[1]:.6f}")

        # Verify it's not zero
        if i == 0:
            if motor_signal[0] < 0.5:
                print("  ⚠️  WARNING: Forward signal unexpectedly low on first step!")
            if abs(motor_signal[1]) < 0.01:
                print("  ⚠️  WARNING: Turn signal unexpectedly small!")

    print("\n" + "="*70)
    print("BRAIN TEST COMPLETE")
    print("="*70)

    # Test with different headings to show bilateral sensing works
    print("\n" + "="*70)
    print("TESTING BILATERAL SENSING WITH DIFFERENT HEADINGS")
    print("="*70)

    test_pos = np.array([35.0, 35.0, 1.8])

    for test_heading_deg in [0, 45, 90, 135, 180]:
        test_heading = np.radians(test_heading_deg)

        # Reset brain history for clean test
        brain._concentration_history = []

        motor_signal = brain.step(odor_field, test_pos, test_heading)

        print(f"\nHeading {test_heading_deg:3d}°: forward={motor_signal[0]:.4f}, turn={motor_signal[1]:.4f}")


if __name__ == "__main__":
    test_brain_isolated()
