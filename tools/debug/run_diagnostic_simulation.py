#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic Simulation Test

Runs a short physics-based simulation and diagnoses:
1. Joint angle recording (critical for fixing analyzer)
2. Z height stability (sinking issues)
3. Motor command effectiveness
4. CPG functioning
5. Brain-physics pipeline integration

This is the key test to verify all fixes are working together.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import pickle

# Configure stdout to handle UTF-8 characters on Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from flygym import Fly, SingleFlySimulation
    from flygym.arena import FlatTerrain
    from flygym.preprogrammed import all_leg_dofs
    from olfaction.odor_field import OdorField
    from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
    from controllers.brain_fly import BrainFly
    HAS_FLYGYM = True
except ImportError as e:
    print(f"Error: Required modules not available: {e}")
    HAS_FLYGYM = False
    sys.exit(1)


def run_diagnostic_simulation(duration=2.0, output_dir=None):
    """Run short diagnostic simulation."""
    print("="*70)
    print("DIAGNOSTIC SIMULATION TEST")
    print("="*70)
    
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = PROJECT_ROOT / "outputs" / "analysis" / "diagnostic_tests" / timestamp
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create components
    print(f"\n[1/3] Initializing components...")
    
    odor_field = OdorField(
        sources=(50, 50, 5),
        sigma=8.0,
        amplitude=100.0
    )
    
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=1.2,
        forward_scale=1.0,
        turn_scale=0.8,
        temporal_gradient_gain=50.0
    )
    
    # Create FlyGym fly with all features
    fly = BrainFly(
        brain=brain,
        odor_field=odor_field,
        timestep=1e-4,
        init_pose="tripod",
        actuated_joints=all_leg_dofs,
        control="position",
        spawn_pos=(35.0, 35.0, 0.5),
        motor_mode="direct_joints",
        enable_adhesion=True,
    )
    
    # Create simulation
    sim = SingleFlySimulation(
        fly=fly,
        arena=FlatTerrain(),
        timestep=1e-4,
    )
    
    print(f"  ✓ Odor field: source at (50, 50, 5), sigma=8.0mm")
    print(f"  ✓ Brain: ImprovedOlfactoryBrain with temporal gradient")
    print(f"  ✓ Fly: BrainFly with CPG controller")
    print(f"  ✓ Simulation: FlyGym with physics (MuJoCo)")
    
    # Run simulation
    print(f"\n[2/3] Running simulation ({duration}s)...")
    
    obs, info = sim.reset()
    
    trajectory_data = {
        "times": [],
        "positions": [],
        "headings": [],
        "z_heights": [],
        "joint_angles": [],
        "brain_actions": [],
        "odor_concs": [],
        "femur_angles": [],  # For detailed analysis
    }
    
    n_steps = int(duration / 1e-4)
    
    for step in range(n_steps):
        # Get action and extract joint angles
        action = fly.step(obs)
        joint_angles_commanded = None
        
        if isinstance(action, dict) and "joints" in action:
            joint_angles_commanded = action["joints"].copy()
        elif isinstance(action, np.ndarray) and len(action) == 42:
            joint_angles_commanded = action.copy()
        
        # Step simulation
        obs, reward, terminated, truncated, info = sim.step(action)
        
        # Extract data
        if "fly" in obs:
            position = np.array(obs["fly"][0])
            orientation = np.array(obs["fly"][2])
            heading = float(orientation[2])
        else:
            position = np.zeros(3)
            heading = 0.0
        
        conc = float(odor_field.concentration_at(position))
        brain_action = fly._last_motor_signal.copy() if hasattr(fly, '_last_motor_signal') else np.array([0, 0])
        
        # Store data
        current_time = step * 1e-4
        trajectory_data["times"].append(current_time)
        trajectory_data["positions"].append(position.copy())
        trajectory_data["headings"].append(heading)
        trajectory_data["z_heights"].append(float(position[2]))
        trajectory_data["brain_actions"].append(brain_action.copy())
        trajectory_data["odor_concs"].append(conc)
        
        # Store joint angles
        if joint_angles_commanded is not None:
            trajectory_data["joint_angles"].append(joint_angles_commanded)
            # Extract femur angles (index 3 per leg: 0, 7, 14, 21, 28, 35)
            femur = [joint_angles_commanded[i] for i in [3, 10, 17, 24, 31, 38]]
            trajectory_data["femur_angles"].append(femur)
        else:
            trajectory_data["joint_angles"].append(np.zeros(42))
            trajectory_data["femur_angles"].append(np.zeros(6))
        
        # Progress
        if (step + 1) % max(1, n_steps // 10) == 0:
            percent = (step + 1) / n_steps * 100
            z = position[2]
            print(f"  Progress: {percent:.0f}% | Step {step+1}/{n_steps} | Z={z:.3f} mm | Conc={conc:.4f}")
        
        if terminated or truncated:
            print(f"  Simulation terminated early at step {step}")
            break
    
    # Convert lists to arrays
    for key in ["times", "positions", "headings", "z_heights", "joint_angles", "brain_actions", "odor_concs", "femur_angles"]:
        trajectory_data[key] = np.array(trajectory_data[key])
    
    print(f"  ✓ Completed {len(trajectory_data['times'])} steps")
    
    # Analyze data
    print(f"\n[3/3] Analyzing results...")
    
    # Check joint angle recording
    print("\nJOINT ANGLE ANALYSIS:")
    joint_angles = trajectory_data["joint_angles"]
    print(f"  Shape: {joint_angles.shape}")
    print(f"  Min: {np.min(joint_angles):.4f}, Max: {np.max(joint_angles):.4f}")
    print(f"  Non-zero elements: {np.count_nonzero(joint_angles)} / {joint_angles.size}")
    
    if np.count_nonzero(joint_angles) == 0:
        print(f"  ✗ WARNING: All joint angles are ZERO! Data not being recorded!")
    elif np.count_nonzero(joint_angles) < joint_angles.size * 0.5:
        print(f"  ⚠ WARNING: Many joint angles are zero - recording may be incomplete")
    else:
        print(f"  ✓ Joint angles properly recorded")
    
    # Check Z height stability
    print("\nZ HEIGHT STABILITY ANALYSIS:")
    z_heights = trajectory_data["z_heights"]
    z_mean = np.mean(z_heights)
    z_min = np.min(z_heights)
    z_max = np.max(z_heights)
    z_std = np.std(z_heights)
    z_range = z_max - z_min
    
    print(f"  Mean Z: {z_mean:.3f} mm")
    print(f"  Min Z: {z_min:.3f} mm, Max Z: {z_max:.3f} mm")
    print(f"  Range: {z_range:.3f} mm")
    print(f"  Std Dev: {z_std:.3f} mm")
    
    if z_range > 2.0:
        print(f"  ✗ CRITICAL: Z height varies too much (>2mm)! This causes sinking!")
    elif z_range > 0.5:
        print(f"  ⚠ WARNING: Z height somewhat unstable (>0.5mm variation)")
    else:
        print(f"  ✓ Z height stable (<0.5mm variation)")
    
    # Check motor commands
    print("\nMOTOR COMMAND ANALYSIS:")
    brain_actions = trajectory_data["brain_actions"]
    print(f"  Forward range: [{np.min(brain_actions[:, 0]):.3f}, {np.max(brain_actions[:, 0]):.3f}]")
    print(f"  Turn range: [{np.min(brain_actions[:, 1]):.3f}, {np.max(brain_actions[:, 1]):.3f}]")
    print(f"  Mean forward: {np.mean(brain_actions[:, 0]):.3f}")
    print(f"  Mean turn: {np.mean(brain_actions[:, 1]):.3f}")
    
    # Check feasmur angles
    print("\nFEMUR ANGLE ANALYSIS (Critical for support):")
    femur_angles = trajectory_data["femur_angles"]
    print(f"  Range: [{np.min(femur_angles):.4f}, {np.max(femur_angles):.4f}]")
    print(f"  Mean: {np.mean(femur_angles):.4f}")
    print(f"  Valid range: [-1.5, -0.2]")
    
    if np.min(femur_angles) >= -1.5 and np.max(femur_angles) <= -0.2:
        print(f"  ✓ Femur angles WITHIN valid range")
    else:
        print(f"  ✗ WARNING: Some femur angles OUT OF range!")
    
    # Save data
    print("\nSAVING DATA:")
    
    # Save pickle
    pkl_path = output_dir / "simulation_data.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(trajectory_data, f)
    print(f"  ✓ Saved: {pkl_path}")
    
    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Diagnostic Simulation: Physics Pipeline Verification", fontsize=14, fontweight='bold')
    
    # Z height over time
    ax = axes[0, 0]
    ax.plot(trajectory_data["times"], trajectory_data["z_heights"], 'b-', linewidth=1.5)
    ax.axhline(y=z_mean, color='g', linestyle='--', label=f'Mean: {z_mean:.2f}mm')
    ax.fill_between(trajectory_data["times"], z_min, z_max, alpha=0.2, color='r', label=f'Range: {z_range:.2f}mm')
    ax.set_ylabel('Z Height (mm)', fontsize=11)
    ax.set_title('Z Height Over Time (Sinking Check)', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Motor commands
    ax = axes[0, 1]
    ax.plot(trajectory_data["times"], trajectory_data["brain_actions"][:, 0], 'b-', label='Forward', linewidth=1.5)
    ax.plot(trajectory_data["times"], trajectory_data["brain_actions"][:, 1], 'r-', label='Turn', linewidth=1.5)
    ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax.set_ylabel('Command [-1, 1]', fontsize=11)
    ax.set_title('Brain Motor Commands', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Odor concentration
    ax = axes[1, 0]
    ax.plot(trajectory_data["times"], trajectory_data["odor_concs"], 'g-', linewidth=1.5)
    ax.set_ylabel('Odor Concentration', fontsize=11)
    ax.set_title('Odor Field Detection', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Femur angles (joint tracking)
    ax = axes[1, 1]
    ax.plot(trajectory_data["times"], trajectory_data["femur_angles"], alpha=0.6, linewidth=1)
    ax.axhline(y=-1.5, color='r', linestyle='--', alpha=0.5, label='Min valid: -1.5')
    ax.axhline(y=-0.2, color='r', linestyle='--', alpha=0.5, label='Max valid: -0.2')
    ax.set_ylabel('Femur Angle (rad)', fontsize=11)
    ax.set_title('Femur Joint Angles (6 legs)', fontsize=12)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    fig_path = output_dir / "diagnostic_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  ✓ Saved: {fig_path}")
    
    # Save text report
    report_path = output_dir / "diagnostic_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("="*70 + "\n")
        f.write("DIAGNOSTIC SIMULATION REPORT\n")
        f.write("="*70 + "\n\n")
        
        f.write("SIMULATION PARAMETERS:\n")
        f.write(f"  Duration: {duration}s\n")
        f.write(f"  Timestep: 1e-4s (10kHz)\n")
        f.write(f"  Total steps: {len(trajectory_data['times'])}\n\n")
        
        f.write("JOINT ANGLE RECORDING:\n")
        f.write(f"  Shape: {joint_angles.shape}\n")
        f.write(f"  Min: {np.min(joint_angles):.4f}, Max: {np.max(joint_angles):.4f}\n")
        f.write(f"  Non-zero: {np.count_nonzero(joint_angles)} / {joint_angles.size}\n")
        f.write(f"  Status: {'✓ OK' if np.count_nonzero(joint_angles) > 0 else '✗ FAILED'}\n\n")
        
        f.write("Z HEIGHT STABILITY:\n")
        f.write(f"  Mean: {z_mean:.3f}mm\n")
        f.write(f"  Min: {z_min:.3f}mm, Max: {z_max:.3f}mm\n")
        f.write(f"  Range: {z_range:.3f}mm\n")
        f.write(f"  Std Dev: {z_std:.3f}mm\n")
        f.write(f"  Status: {'✓ OK' if z_range < 0.5 else ('✗ SINKING' if z_range > 2.0 else '⚠ WARNING')}\n\n")
        
        f.write("MOTOR COMMANDS:\n")
        f.write(f"  Forward: [{np.min(brain_actions[:, 0]):.3f}, {np.max(brain_actions[:, 0]):.3f}]\n")
        f.write(f"  Turn: [{np.min(brain_actions[:, 1]):.3f}, {np.max(brain_actions[:, 1]):.3f}]\n\n")
        
        f.write("FEMUR ANGLES:\n")
        f.write(f"  Range: [{np.min(femur_angles):.4f}, {np.max(femur_angles):.4f}]\n")
        f.write(f"  Valid: [-1.5, -0.2]\n")
        f.write(f"  Status: {'✓ OK' if np.min(femur_angles) >= -1.5 and np.max(femur_angles) <= -0.2 else '✗ OUT OF RANGE'}\n")
    
    print(f"  ✓ Saved: {report_path}")
    
    print("\n" + "="*70)
    print(f"✓ Diagnostic simulation completed! Output in: {output_dir}")
    print("="*70)
    
    return output_dir, trajectory_data


if __name__ == "__main__":
    output_dir, data = run_diagnostic_simulation(duration=2.0)
    plt.show()
