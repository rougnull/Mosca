#!/usr/bin/env python3
"""
Consolidated test suite for brain-motor connection.

This script runs all component tests sequentially:
1. Brain isolated test - Tests brain algorithm without physics
2. Observation extraction test - Tests BrainFly observation extraction
3. Short physics simulation - Tests full integration with physics

All tests have been extended to run more steps for more noticeable movement.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from olfaction.odor_field import OdorField

# Check if FlyGym is available (optional for first two tests)
HAS_FLYGYM = False
try:
    from flygym import Fly, Camera
    from flygym.simulation import SingleFlySimulation
    from flygym.arena import FlatTerrain
    from flygym.preprogrammed import all_leg_dofs
    from controllers.brain_fly import BrainFly
    HAS_FLYGYM = True
except ImportError:
    print("⚠️  WARNING: FlyGym not available. Physics simulation test will be skipped.")


def test_brain_isolated():
    """Test 1: Brain with simulated trajectory (no physics)."""
    print("\n" + "="*70)
    print("TEST 1: BRAIN ISOLATED TEST")
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

    # Simulate longer trajectory for more noticeable movement (15 steps instead of 5)
    # Create a curved path moving toward the source
    positions = []
    headings = []

    # Starting position
    x, y, z = 35.015, 35.007, 1.783
    heading = 0.837  # ~48°

    # Simulate 15 steps with small movements
    for i in range(15):
        positions.append(np.array([x, y, z]))
        headings.append(heading)

        # Update position based on heading (small steps)
        x += 0.05 * np.cos(heading)
        y += 0.05 * np.sin(heading)
        z += 0.002 * i  # Slight upward drift

        # Update heading based on previous turn (simulate turning)
        heading += 0.005 * i

    print(f"\nSimulating {len(positions)} steps with curved trajectory")
    print("\n" + "="*70)
    print("TESTING BRAIN WITH TRAJECTORY")
    print("="*70)

    turn_signals = []
    forward_signals = []

    for i, (pos, heading_angle) in enumerate(zip(positions, headings)):
        if i < 3 or i >= len(positions) - 3:  # Show first and last 3 steps
            print(f"\n--- Step {i} ---")
            print(f"Position: [{pos[0]:.6f}, {pos[1]:.6f}, {pos[2]:.6f}]")
            print(f"Heading: {heading_angle:.6f} rad ({np.degrees(heading_angle):.2f}°)")

        # Get odor concentrations
        conc_center = odor_field.concentration_at(pos)

        # Calculate bilateral positions
        left_angle = heading_angle + np.pi / 2
        right_angle = heading_angle - np.pi / 2

        left_pos = pos + 1.2 * np.array([np.cos(left_angle), np.sin(left_angle), 0])
        right_pos = pos + 1.2 * np.array([np.cos(right_angle), np.sin(right_angle), 0])

        conc_left = odor_field.concentration_at(left_pos)
        conc_right = odor_field.concentration_at(right_pos)

        if i < 3 or i >= len(positions) - 3:
            print(f"Conc center: {conc_center:.6f}")
            print(f"Conc left: {conc_left:.6f}")
            print(f"Conc right: {conc_right:.6f}")
            print(f"Gradient (L-R): {conc_left - conc_right:.6f}")

        # Call brain
        motor_signal = brain.step(odor_field, pos, heading_angle)

        turn_signals.append(motor_signal[1])
        forward_signals.append(motor_signal[0])

        if i < 3 or i >= len(positions) - 3:
            print(f">>> Motor signal: forward={motor_signal[0]:.6f}, turn={motor_signal[1]:.6f}")

    # Summary statistics
    print("\n" + "="*70)
    print("BRAIN TEST COMPLETE - SUMMARY")
    print("="*70)

    turn_signals_array = np.array(turn_signals)
    forward_signals_array = np.array(forward_signals)

    print(f"\nForward signals: min={np.min(forward_signals_array):.6f}, max={np.max(forward_signals_array):.6f}, mean={np.mean(forward_signals_array):.6f}")
    print(f"Turn signals: min={np.min(turn_signals_array):.6f}, max={np.max(turn_signals_array):.6f}, mean={np.mean(turn_signals_array):.6f}")

    # Verify results
    if np.max(np.abs(turn_signals_array)) < 0.01:
        print("\n❌ FAILED: Turn signals are too small!")
        return False
    else:
        print("\n✅ PASSED: Brain generates appropriate turn signals")
        return True


def test_observation_extraction():
    """Test 2: BrainFly observation extraction from SingleFlySimulation format."""
    print("\n" + "="*70)
    print("TEST 2: BRAINFLY OBSERVATION EXTRACTION")
    print("="*70)

    # Import BrainFly
    try:
        from controllers.brain_fly import BrainFly
    except ImportError:
        print("❌ ERROR: Cannot import BrainFly")
        return False

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
    pos_correct = np.allclose(extracted_pos, mock_obs['fly'][0])
    print(f"  Correct: {pos_correct}")

    print("\nTesting _extract_heading():")
    extracted_heading = fly._extract_heading(mock_obs)
    print(f"  Extracted: {extracted_heading:.6f} rad ({np.degrees(extracted_heading):.2f}°)")
    print(f"  Expected: {mock_obs['fly'][2][2]:.6f} rad ({np.degrees(mock_obs['fly'][2][2]):.2f}°)")
    heading_correct = np.isclose(extracted_heading, mock_obs['fly'][2][2])
    print(f"  Correct: {heading_correct}")

    # Now test brain.step() with extracted values
    print("\n" + "-"*70)
    print("Testing brain.step() with extracted values:")

    motor_signal = brain.step(odor_field, extracted_pos, extracted_heading)
    print(f"  Motor signal: forward={motor_signal[0]:.6f}, turn={motor_signal[1]:.6f}")

    motor_correct = abs(motor_signal[1]) >= 1e-6
    if not motor_correct:
        print("  ❌ ERROR: Turn signal is essentially zero!")
    else:
        print("  ✅ SUCCESS: Turn signal is non-zero!")

    # Test with multiple observations to show consistency
    print("\n" + "-"*70)
    print("Testing with multiple observations:")

    test_observations = []
    for i in range(10):
        angle = 0.8365 + i * 0.05  # Vary the heading
        test_observations.append({
            "fly": (
                np.array([35.015 + i * 0.1, 35.007 + i * 0.1, 1.783]),
                np.array([0.923, 0.0, 0.0, 0.385]),
                np.array([1.5705, 0.00016, angle]),
            )
        })

    print(f"  Testing {len(test_observations)} different observations...")
    all_extractions_ok = True

    for i, obs in enumerate(test_observations):
        pos = fly._extract_head_position(obs)
        heading = fly._extract_heading(obs)
        signal = brain.step(odor_field, pos, heading)

        if pos is None or heading is None:
            all_extractions_ok = False
            print(f"  ❌ Observation {i}: Extraction failed")
        elif i % 3 == 0:  # Show every 3rd result
            print(f"  Step {i}: heading={heading:.4f} rad, turn={signal[1]:.6f}")

    if all_extractions_ok:
        print("  ✅ All extractions successful")

    # Test with incorrect obs structure (dict instead of tuple) - FIXED ERROR HANDLING
    print("\n" + "="*70)
    print("TESTING WITH INCORRECT OBSERVATION STRUCTURE")
    print("="*70)

    wrong_obs = {
        "fly": {
            "position": np.array([35.015, 35.007, 1.783]),
            "orientation": np.array([1.5705, 0.00016, 0.8365]),
        }
    }

    print("\nWrong observation structure (dict instead of tuple):")
    print(f"  obs['fly']['position']: {wrong_obs['fly']['position']}")

    extracted_pos_wrong = fly._extract_head_position(wrong_obs)
    extracted_heading_wrong = fly._extract_heading(wrong_obs)

    print(f"  Extracted position: {extracted_pos_wrong}")

    # FIXED: Handle None return value properly
    if extracted_heading_wrong is None:
        print(f"  Extracted heading: None (extraction failed as expected)")
        print("  ✅ As expected, extraction fails gracefully with wrong structure")
    else:
        print(f"  Extracted heading: {extracted_heading_wrong:.6f}")
        if extracted_heading_wrong == 0:
            print("  ✅ As expected, extraction returns fallback value with wrong structure")

    print("\n" + "="*70)
    print("OBSERVATION EXTRACTION TEST COMPLETE")
    print("="*70)

    # Overall pass/fail
    overall_pass = pos_correct and heading_correct and motor_correct and all_extractions_ok
    if overall_pass:
        print("\n✅ PASSED: Observation extraction working correctly")
        return True
    else:
        print("\n❌ FAILED: Some observation extraction tests failed")
        return False


def test_short_simulation():
    """Test 3: Short physics simulation with extensive debug logging."""
    print("\n" + "="*70)
    print("TEST 3: SHORT PHYSICS SIMULATION")
    print("="*70)

    if not HAS_FLYGYM:
        print("\n⚠️  SKIPPED: FlyGym not available")
        print("   Install FlyGym to run this test: pip install flygym")
        return None

    # Create odor field
    odor_field = OdorField(
        sources=(50, 50, 5),
        sigma=8.0,
        amplitude=100.0
    )

    # Create brain
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8,
        temporal_gradient_gain=10.0
    )

    start_pos = (35.0, 35.0, 0.5)
    timestep = 1e-4  # Physics timestep

    # Extended simulation: 200 steps instead of 50 for more noticeable movement
    num_steps = 200

    print(f"\nConfiguration:")
    print(f"  Odor source: (50, 50, 5)")
    print(f"  Start pos: {start_pos}")
    print(f"  Brain: ImprovedOlfactoryBrain")
    print(f"  Simulation steps: {num_steps} ({num_steps * timestep:.4f}s)")
    print(f"  Simulation timestep: {timestep}s")
    print(f"  Actuated joints: {len(all_leg_dofs)} DoF")

    # Create BrainFly
    fly = BrainFly(
        brain=brain,
        odor_field=odor_field,
        timestep=timestep,  # CRITICAL: Pass simulation timestep to CPG controller
        init_pose="tripod",
        actuated_joints=all_leg_dofs,
        control="position",
        spawn_pos=start_pos,
        motor_mode="direct_joints",
        enable_adhesion=True,
    )

    # Create simulation
    sim = SingleFlySimulation(
        fly=fly,
        arena=FlatTerrain(),
        timestep=timestep,
    )

    obs, info = sim.reset()

    print("\n" + "="*70)
    print("RUNNING SIMULATION")
    print("="*70)

    brain_actions_log = []
    positions_log = []
    headings_log = []

    for step in range(num_steps):
        # Get action from BrainFly
        action = fly.step(obs)

        # Execute physics step
        obs, reward, terminated, truncated, info = sim.step(action)

        # Log data
        if "fly" in obs:
            position = obs["fly"][0]
            euler = obs["fly"][2]
            heading = euler[2]
        else:
            position = np.zeros(3)
            heading = 0.0

        brain_action = fly._last_motor_signal.copy()

        brain_actions_log.append(brain_action)
        positions_log.append(position)
        headings_log.append(heading)

        # Show first 5, last 5, and every 40th step
        if step < 5 or step >= num_steps - 5 or step % 40 == 0:
            print(f"\nStep {step}:")
            print(f"  Position: [{position[0]:.6f}, {position[1]:.6f}, {position[2]:.6f}]")
            print(f"  Heading: {heading:.6f} rad ({np.degrees(heading):.2f}°)")
            print(f"  Brain action: forward={brain_action[0]:.6f}, turn={brain_action[1]:.6e}")

    print("\n" + "="*70)
    print("SIMULATION COMPLETE - ANALYSIS")
    print("="*70)

    brain_actions_array = np.array(brain_actions_log)
    forward_actions = brain_actions_array[:, 0]
    turn_actions = brain_actions_array[:, 1]

    print(f"\nBrain Actions Statistics:")
    print(f"  Forward: min={np.min(forward_actions):.6f}, max={np.max(forward_actions):.6f}, mean={np.mean(forward_actions):.6f}")
    print(f"  Turn: min={np.min(turn_actions):.6e}, max={np.max(turn_actions):.6e}, mean={np.mean(turn_actions):.6e}")
    print(f"  Turn std: {np.std(turn_actions):.6e}")

    positions_array = np.array(positions_log)
    headings_array = np.array(headings_log)

    # Calculate distance traveled
    distance_traveled = np.sum(np.sqrt(np.sum(np.diff(positions_array[:, :2], axis=0)**2, axis=1)))

    print(f"\nMovement Statistics:")
    print(f"  Distance traveled (XY): {distance_traveled:.6f} mm")
    print(f"  Initial position: [{positions_array[0, 0]:.6f}, {positions_array[0, 1]:.6f}, {positions_array[0, 2]:.6f}]")
    print(f"  Final position: [{positions_array[-1, 0]:.6f}, {positions_array[-1, 1]:.6f}, {positions_array[-1, 2]:.6f}]")
    print(f"  Position change: ΔX={positions_array[-1, 0] - positions_array[0, 0]:.6f}, ΔY={positions_array[-1, 1] - positions_array[0, 1]:.6f}")
    print(f"  Initial heading: {headings_array[0]:.6f} rad ({np.degrees(headings_array[0]):.2f}°)")
    print(f"  Final heading: {headings_array[-1]:.6f} rad ({np.degrees(headings_array[-1]):.2f}°)")
    print(f"  Heading change: {headings_array[-1] - headings_array[0]:.6f} rad ({np.degrees(headings_array[-1] - headings_array[0]):.2f}°)")

    print(f"\nZ-axis (vertical) Statistics:")
    print(f"  Initial Z: {positions_array[0, 2]:.6f}")
    print(f"  Final Z: {positions_array[-1, 2]:.6f}")
    print(f"  Min Z: {np.min(positions_array[:, 2]):.6f}")
    print(f"  Max Z: {np.max(positions_array[:, 2]):.6f}")

    # Check for issues
    has_issues = False

    if np.max(np.abs(turn_actions)) < 1e-6:
        print("\n❌ PROBLEM: Turn actions are essentially zero!")
        print("   The observation extraction or brain call is failing.")
        has_issues = True
    else:
        print("\n✅ SUCCESS: Turn actions are non-zero!")
        print(f"   Turn range: [{np.min(turn_actions):.6f}, {np.max(turn_actions):.6f}]")

    if np.min(positions_array[:, 2]) < 0:
        print("⚠️  WARNING: Ground penetration detected")
        has_issues = True

    if distance_traveled < 0.01:
        print("⚠️  WARNING: Fly barely moved (distance < 0.01mm)")
        has_issues = True
    else:
        print(f"✅ Fly traveled {distance_traveled:.6f} mm")

    # Save test data to outputs/tests
    try:
        import pickle
        from datetime import datetime
        from pathlib import Path

        # Create timestamp for unique filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        output_dir = Path(__file__).parent.parent / "outputs" / "tests"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data package
        test_data = {
            'timestamp': timestamp,
            'configuration': {
                'odor_source': (50, 50, 5),
                'start_pos': start_pos,
                'timestep': timestep,
                'num_steps': num_steps,
                'simulation_time': num_steps * timestep,
            },
            'brain_actions': brain_actions_array,
            'positions': positions_array,
            'headings': headings_array,
            'statistics': {
                'forward_min': np.min(forward_actions),
                'forward_max': np.max(forward_actions),
                'forward_mean': np.mean(forward_actions),
                'turn_min': np.min(turn_actions),
                'turn_max': np.max(turn_actions),
                'turn_mean': np.mean(turn_actions),
                'turn_std': np.std(turn_actions),
                'distance_traveled': distance_traveled,
                'heading_change': headings_array[-1] - headings_array[0],
                'z_min': np.min(positions_array[:, 2]),
                'z_max': np.max(positions_array[:, 2]),
            },
            'issues': {
                'ground_penetration': np.min(positions_array[:, 2]) < 0,
                'turn_signal_zero': np.max(np.abs(turn_actions)) < 1e-6,
                'minimal_movement': distance_traveled < 0.01,
            }
        }

        # Save to pickle file
        output_file = output_dir / f"physics_test_{timestamp}.pkl"
        with open(output_file, 'wb') as f:
            pickle.dump(test_data, f)

        print(f"\n💾 Test data saved to: {output_file}")

    except Exception as e:
        print(f"\n⚠️  Warning: Could not save test data: {e}")

    return not has_issues


def main():
    """Run all tests sequentially."""
    print("\n" + "="*70)
    print("RUNNING CONSOLIDATED TEST SUITE")
    print("="*70)
    print("\nThis suite tests the brain-motor connection at three levels:")
    print("  1. Brain algorithm in isolation (no physics)")
    print("  2. Observation extraction from FlyGym format")
    print("  3. Full integration with physics simulation")
    print("\n" + "="*70)

    results = {}

    # Test 1: Brain isolated
    try:
        results['brain_isolated'] = test_brain_isolated()
    except Exception as e:
        print(f"\n❌ TEST 1 CRASHED: {e}")
        import traceback
        traceback.print_exc()
        results['brain_isolated'] = False

    # Test 2: Observation extraction
    try:
        results['observation_extraction'] = test_observation_extraction()
    except Exception as e:
        print(f"\n❌ TEST 2 CRASHED: {e}")
        import traceback
        traceback.print_exc()
        results['observation_extraction'] = False

    # Test 3: Short simulation (only if FlyGym available)
    if HAS_FLYGYM:
        try:
            results['short_simulation'] = test_short_simulation()
        except Exception as e:
            print(f"\n❌ TEST 3 CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results['short_simulation'] = False
    else:
        results['short_simulation'] = None

    # Final summary
    print("\n" + "="*70)
    print("FINAL TEST RESULTS")
    print("="*70)

    for test_name, result in results.items():
        status = "✅ PASSED" if result is True else ("⚠️  SKIPPED" if result is None else "❌ FAILED")
        print(f"  {test_name}: {status}")

    # Overall status
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)

    print(f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped out of {total} tests")

    if failed > 0:
        print("\n❌ OVERALL: Some tests failed")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠️  OVERALL: No tests passed (all skipped or crashed)")
        sys.exit(2)
    else:
        print("\n✅ OVERALL: All available tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
