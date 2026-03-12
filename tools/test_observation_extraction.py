#!/usr/bin/env python3
"""
Test BrainFly observation extraction with mock observations.

This tests that BrainFly correctly extracts position and heading
from SingleFlySimulation observation structure.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controllers.brain_fly import BrainFly
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from olfaction.odor_field import OdorField


def test_observation_extraction():
    """Test observation extraction from SingleFlySimulation format."""
    print("="*70)
    print("TESTING BRAINFLY OBSERVATION EXTRACTION")
    print("="*70)

    # Create brain and odor field
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8,
        temporal_gradient_gain=10.0
    )

    odor_field = OdorField(
        sources=(50, 50, 5),
        sigma=8.0,
        amplitude=100.0
    )

    # Create mock BrainFly (without full Fly initialization)
    # We'll manually test the extraction methods
    class MockBrainFly:
        def __init__(self, brain, odor_field):
            self.brain = brain
            self.odor_field = odor_field
            self._last_heading = None

        # Copy the extraction methods from BrainFly
        _extract_head_position = BrainFly._extract_head_position
        _extract_heading = BrainFly._extract_heading
        _quaternion_to_yaw = BrainFly._quaternion_to_yaw

    fly = MockBrainFly(brain, odor_field)

    # Create mock observation in SingleFlySimulation format
    # obs["fly"] = (position, quaternion, euler_angles, ...)
    mock_obs = {
        "fly": (
            np.array([35.015, 35.007, 1.783]),  # position
            np.array([0.923, 0.0, 0.0, 0.385]),  # quaternion (example)
            np.array([1.5705, 0.00016, 0.8365]),  # euler [roll, pitch, yaw]
        )
    }

    print("\nMock observation structure:")
    print(f"  obs['fly'][0] (position): {mock_obs['fly'][0]}")
    print(f"  obs['fly'][1] (quaternion): {mock_obs['fly'][1]}")
    print(f"  obs['fly'][2] (euler): {mock_obs['fly'][2]}")
    print(f"  Expected heading (yaw): {mock_obs['fly'][2][2]:.6f} rad ({np.degrees(mock_obs['fly'][2][2]):.2f}°)")

    # Test extraction
    print("\n" + "-"*70)
    print("Testing _extract_head_position():")
    extracted_pos = fly._extract_head_position(mock_obs)
    print(f"  Extracted: {extracted_pos}")
    print(f"  Correct: {np.allclose(extracted_pos, mock_obs['fly'][0])}")

    print("\nTesting _extract_heading():")
    extracted_heading = fly._extract_heading(mock_obs)
    print(f"  Extracted: {extracted_heading:.6f} rad ({np.degrees(extracted_heading):.2f}°)")
    print(f"  Expected: {mock_obs['fly'][2][2]:.6f} rad ({np.degrees(mock_obs['fly'][2][2]):.2f}°)")
    print(f"  Correct: {np.isclose(extracted_heading, mock_obs['fly'][2][2])}")

    # Now test brain.step() with extracted values
    print("\n" + "-"*70)
    print("Testing brain.step() with extracted values:")

    motor_signal = brain.step(odor_field, extracted_pos, extracted_heading)
    print(f"  Motor signal: forward={motor_signal[0]:.6f}, turn={motor_signal[1]:.6f}")

    if abs(motor_signal[1]) < 1e-6:
        print("  ❌ ERROR: Turn signal is essentially zero!")
    else:
        print("  ✅ SUCCESS: Turn signal is non-zero!")

    # Test with incorrect obs structure (dict instead of tuple)
    print("\n" + "="*70)
    print("TESTING WITH INCORRECT OBSERVATION STRUCTURE")
    print("="*70)

    wrong_obs = {
        "fly": {
            "position": np.array([35.015, 35.007, 1.783]),
            "orientation": np.array([1.5705, 0.00016, 0.8365]),
        }
    }

    print("\nWrong observation structure (dict):")
    print(f"  obs['fly']['position']: {wrong_obs['fly']['position']}")

    extracted_pos_wrong = fly._extract_head_position(wrong_obs)
    extracted_heading_wrong = fly._extract_heading(wrong_obs)

    print(f"  Extracted position: {extracted_pos_wrong}")
    print(f"  Extracted heading: {extracted_heading_wrong:.6f}")

    if np.allclose(extracted_pos_wrong, 0) or extracted_heading_wrong == 0:
        print("  ⚠️  As expected, extraction fails with wrong structure")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_observation_extraction()
