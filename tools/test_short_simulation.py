#!/usr/bin/env python3
"""
Run a SHORT physics simulation with extensive debug logging.

This runs only 50 steps (0.005 seconds) to quickly verify the
brain-motor connection is working.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Check if FlyGym is available
try:
    from flygym import Fly, Camera
    from flygym.simulation import SingleFlySimulation
    from flygym.arena import FlatTerrain
    from flygym.preprogrammed import all_leg_dofs  # Use FlyGym's predefined DoF list
    HAS_FLYGYM = True
except ImportError:
    print("ERROR: FlyGym not available")
    print("This test requires FlyGym installed")
    sys.exit(1)

from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from controllers.brain_fly import BrainFly
from olfaction.odor_field import OdorField


def run_short_simulation():
    """Run ultra-short simulation for debugging."""
    print("="*70)
    print("SHORT PHYSICS SIMULATION FOR DEBUG")
    print("="*70)

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

    print(f"\nConfiguration:")
    print(f"  Odor source: (50, 50, 5)")
    print(f"  Start pos: {start_pos}")
    print(f"  Brain: ImprovedOlfactoryBrain")
    print(f"  Simulation steps: 50 (0.005s)")
    print(f"  Actuated joints: {len(all_leg_dofs)} DoF")

    # Create BrainFly
    fly = BrainFly(
        brain=brain,
        odor_field=odor_field,
        init_pose="tripod",
        actuated_joints=all_leg_dofs,  # Use FlyGym's predefined DoF list
        control="position",
        spawn_pos=start_pos,
        motor_mode="direct_joints",
        enable_adhesion=True,
    )

    # Create simulation
    sim = SingleFlySimulation(
        fly=fly,
        arena=FlatTerrain(),
        timestep=1e-4,
    )

    obs, info = sim.reset()

    print("\n" + "="*70)
    print("RUNNING SIMULATION")
    print("="*70)

    brain_actions_log = []
    positions_log = []
    headings_log = []

    for step in range(50):
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

        if step < 5 or step == 49:
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

    # Check if turn is effectively zero
    if np.max(np.abs(turn_actions)) < 1e-6:
        print("\n❌ PROBLEM: Turn actions are essentially zero!")
        print("   The observation extraction or brain call is failing.")
    else:
        print("\n✅ SUCCESS: Turn actions are non-zero!")
        print(f"   Turn range: [{np.min(turn_actions):.6f}, {np.max(turn_actions):.6f}]")

    positions_array = np.array(positions_log)
    print(f"\nPosition:")
    print(f"  Initial Z: {positions_array[0, 2]:.6f}")
    print(f"  Final Z: {positions_array[-1, 2]:.6f}")
    print(f"  Min Z: {np.min(positions_array[:, 2]):.6f}")

    if np.min(positions_array[:, 2]) < 0:
        print("  ⚠️  Ground penetration detected")


if __name__ == "__main__":
    run_short_simulation()
