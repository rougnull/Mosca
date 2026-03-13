#!/usr/bin/env python3
"""
Enhanced Simulation Data Analysis Tool

Improved version that correctly reads and analyzes simulation pickle files.

This tool analyzes the trajectory_data.pkl files saved by run_physics_based_simulation.py
and provides detailed diagnostics on:
1. Joint angles (all 42 DoF) - location and values
2. Z height stability (sinking diagnosis) 
3. Motor command effectiveness
4. Brain response to odor
5. CPG gait coordination
6. Ground contact and forces

USAGE:
    python tools/analyze_enhanced.py <path_to_simulation_data.pkl>
    
EXAMPLE:
    python tools/analyze_enhanced.py outputs/simulations/physics_3d/2026-03-12_21_45/simulation_data.pkl
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

try:
    import json
    HAS_JSON = True
except ImportError:
    HAS_JSON = False


def load_pickle_data(pkl_path):
    """Load pickle file and handle errors."""
    pkl_path = Path(pkl_path)
    
    if not pkl_path.exists():
        print(f"Error: File not found: {pkl_path}")
        return None
    
    try:
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)
        return data
    except Exception as e:
        print(f"Error loading pickle: {e}")
        return None


def analyze_trajectory_data(data, pkl_path=None):
    """Analyze loaded trajectory data comprehensively."""
    
    print("\n" + "="*70)
    print("ENHANCED SIMULATION DATA ANALYSIS")
    print("="*70)
    
    if pkl_path:
        print(f"\nFile: {pkl_path}")
    
    # Basic structure analysis
    print("\n[1] DATA STRUCTURE:")
    print("-"*70)
    
    if isinstance(data, dict):
        print(f"Type: Dictionary with {len(data)} keys")
        print("Keys found:")
        for key in sorted(data.keys()):
            val = data[key]
            if isinstance(val, np.ndarray):
                print(f"  '{key}': ndarray shape={val.shape}, dtype={val.dtype}")
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], np.ndarray):
                    print(f"  '{key}': list of {len(val)} arrays, first shape={val[0].shape}")
                else:
                    print(f"  '{key}': list of {len(val)} items")
            else:
                print(f"  '{key}': {type(val).__name__}")
    else:
        print(f"Type: {type(data).__name__}")
        return
    
    # Joint angle analysis (CRITICAL)
    print("\n[2] JOINT ANGLE ANALYSIS:")
    print("-"*70)
    
    if "joint_angles" in data:
        joint_angles = data["joint_angles"]
        if isinstance(joint_angles, np.ndarray):
            print(f"Shape: {joint_angles.shape}")
            print(f"Dtype: {joint_angles.dtype}")
            print(f"Range: [{np.min(joint_angles):.6f}, {np.max(joint_angles):.6f}]")
            print(f"Non-zero elements: {np.count_nonzero(joint_angles)} / {joint_angles.size}")
            
            if joint_angles.shape[1] == 42:
                print(f"✓ CORRECT: 42 joint angles per timestep")
                
                # Analyze specific joints
                print("\nJoint ranges (min, max, mean per column):")
                print("  Leg\t Joint\t\t Min\t Max\t Mean")
                print("  " + "-"*60)
                
                legs = ["LF", "LM", "LH", "RF", "RM", "RH"]
                dofs = ["Coxa", "CoxaRoll", "CoxaYaw", "Femur", "FemurRoll", "Tibia", "Tarsus"]
                
                for leg_idx, leg in enumerate(legs):
                    for dof_idx, dof in enumerate(dofs):
                        col_idx = leg_idx * 7 + dof_idx
                        col_data = joint_angles[:, col_idx]
                        col_min = np.min(col_data)
                        col_max = np.max(col_data)
                        col_mean = np.mean(col_data)
                        print(f"  {leg}\t {dof:10s}\t {col_min:7.3f}\t {col_max:7.3f}\t {col_mean:7.3f}")
                    print()
                
                # Femur analysis (critical for sinking)
                print("\nFEMUR ANGLES ANALYSIS (Critical for sinking diagnosis):")
                femur_cols = [3, 10, 17, 24, 31, 38]  # Femur angle for each leg
                femur_data = joint_angles[:, femur_cols]
                femur_min = np.min(femur_data)
                femur_max = np.max(femur_data)
                femur_range = femur_max - femur_min
                
                print(f"  Range: [{femur_min:.4f}, {femur_max:.4f}]")
                print(f"  Spread: {femur_range:.4f}")
                print(f"  Valid range (biological): [-1.5, -0.2]")
                
                if femur_min >= -1.5 and femur_max <= -0.2:
                    print(f"  ✓ Femur angles WITHIN valid biological range")
                else:
                    print(f"  ✗ WARNING: Femur angles OUT OF valid range!")
                    if femur_min < -1.5:
                        print(f"    Too flexed (overshooting extend): {femur_min:.4f} < -1.5")
                    if femur_max > -0.2:
                        print(f"    Too extended: {femur_max:.4f} > -0.2")
            
            elif joint_angles.shape[1] == 2:
                print(f"✗ ERROR: Only {joint_angles.shape[1]} joints found (expecting 42)!")
                print(f"  This is the [forward, turn] command, not joint angles!")
            
            elif all(joint_angles.flatten() == 0):
                print(f"✗ CRITICAL: All joint angles are ZERO!")
                print(f"  Joint angles are not being recorded!")
            else:
                print(f"⚠ Unexpected: {joint_angles.shape[1]} joints (expecting 42)")
    else:
        print("✗ ERROR: 'joint_angles' key not found in data!")
        print(f"  Available keys: {list(data.keys())}")
    
    # Z height analysis
    print("\n[3] Z HEIGHT STABILITY ANALYSIS (Sinking Diagnosis):")
    print("-"*70)
    
    if "positions" in data:
        positions = data["positions"]
        if isinstance(positions, np.ndarray) and positions.shape[1] >= 3:
            z_heights = positions[:, 2]
            z_min = np.min(z_heights)
            z_max = np.max(z_heights)
            z_mean = np.mean(z_heights)
            z_std = np.std(z_heights)
            z_range = z_max - z_min
            
            print(f"Mean Z: {z_mean:.3f} mm")
            print(f"Min Z: {z_min:.3f} mm, Max Z: {z_max:.3f} mm")
            print(f"Range: {z_range:.3f} mm")
            print(f"Std Dev: {z_std:.3f} mm")
            
            # Interpretation
            if z_range > 2.0:
                print(f"\n✗ CRITICAL: Z varies by {z_range:.2f}mm (>2mm threshold)")
                print(f"  FLY IS SINKING! Check:")
                print(f"  1. Are joint angles being applied? (should not be all zeros)")
                print(f"  2. Is femur offset correct? (-0.5 rad)")
                print(f"  3. Is CPG amplitude sufficient? (0.7 baseline)")
            elif z_range > 0.5:
                print(f"\n⚠ WARNING: Z varies by {z_range:.3f}mm (moderate instability)")
            else:
                print(f"\n✓ OK: Z stable (variation {z_range:.3f}mm < 0.5mm)")
            
            # Check for catastrophic failure
            if z_min < 0:
                print(f"\n✗ CATASTROPHIC: Z goes NEGATIVE (below ground)!")
                print(f"  The fly is clipping through the arena!")
    else:
        print("'positions' key not found")
    
    # Motor command analysis
    print("\n[4] MOTOR COMMAND ANALYSIS (Brain output):")
    print("-"*70)
    
    if "brain_actions" in data:
        actions = data["brain_actions"]
        if isinstance(actions, np.ndarray) and actions.shape[1] >= 2:
            forward = actions[:, 0]
            turn = actions[:, 1]
            
            print(f"Forward command:")
            print(f"  Range: [{np.min(forward):.3f}, {np.max(forward):.3f}]")
            print(f"  Mean: {np.mean(forward):.3f}, Std: {np.std(forward):.3f}")
            
            print(f"\nTurn command:")
            print(f"  Range: [{np.min(turn):.3f}, {np.max(turn):.3f}]")
            print(f"  Mean: {np.mean(turn):.3f}, Std: {np.std(turn):.3f}")
            
            # Check if commands are reasonable
            if np.std(forward) < 0.01:
                print(f"\n⚠ WARNING: Forward command barely varies (std={np.std(forward):.6f})")
                print(f"  Brain might not be responding to odor gradient!")
            elif np.mean(forward) < -0.2:
                print(f"\n⚠ WARNING: Mean forward is negative (backing up)")
                print(f"  Check: Is the fly starting far from odor?")
            elif np.mean(forward) > 0.8:
                print(f"\n✓ Good: Fly consistently moving forward toward odor")
    
    # Odor concentration
    print("\n[5] ODOR FIELD RESPONSE:")
    print("-"*70)
    
    if "odor_concentrations" in data:
        concs = data["odor_concentrations"]
        if isinstance(concs, (list, np.ndarray)):
            concs = np.array(concs) if isinstance(concs, list) else concs
            print(f"Concentration range: [{np.min(concs):.6f}, {np.max(concs):.6f}]")
            print(f"Mean: {np.mean(concs):.6f}")
            
            # Check if fly found the odor
            if np.max(concs) > 10:
                print(f"✓ Fly reached high concentration ({np.max(concs):.1f})")
            elif np.max(concs) > 1:
                print(f"⚠ Fly reached moderate concentration ({np.max(concs):.2f})")
            else:
                print(f"⚠ Fly never reached high concentration")
    
    # Temporal analysis
    print("\n[6] SIMULATION DURATION:")
    print("-"*70)
    
    if "times" in data:
        times = data["times"]
        if isinstance(times, (list, np.ndarray)):
            times = np.array(times) if isinstance(times, list) else times
            duration = times[-1]
            n_steps = len(times)
            print(f"Duration: {duration:.2f}s")
            print(f"Total steps: {n_steps}")
            
            if n_steps > 1:
                timestep = times[1] - times[0]
                print(f"Timestep: {timestep:.6f}s ({1/timestep:.0f} Hz)")
    
    print("\n" + "="*70)


def create_analysis_plots(data, pkl_path=None):
    """Create diagnostic plots from trajectory data."""
    
    output_dir = Path(pkl_path).parent if pkl_path else Path(".")
    
    # Extract data
    times = np.array(data.get("times", [])) if "times" in data else np.arange(len(data.get("positions", [])))
    positions = np.array(data["positions"]) if "positions" in data else None
    joint_angles = np.array(data["joint_angles"]) if "joint_angles" in data else None
    brain_actions = np.array(data["brain_actions"]) if "brain_actions" in data else None
    odor_concs = np.array(data["odor_concentrations"]) if "odor_concentrations" in data else None
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Simulation Data Analysis", fontsize=14, fontweight='bold')
    
    # Z height
    if positions is not None and positions.shape[1] >= 3:
        ax = axes[0, 0]
        z = positions[:, 2]
        ax.plot(times, z, 'b-', linewidth=1)
        ax.fill_between(times, z.min(), z.max(), alpha=0.2)
        ax.set_ylabel('Z Height (mm)')
        ax.set_title('Z Height (Sinking Analysis)')
        ax.grid(True, alpha=0.3)
        
        # Add warning if sinking
        z_range = z.max() - z.min()
        if z_range > 2:
            ax.text(0.98, 0.02, f'✗ SINKING: Range {z_range:.2f}mm', 
                   transform=ax.transAxes, ha='right', va='bottom',
                   bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
                   color='white', fontweight='bold')
    
    # Motor commands
    if brain_actions is not None and brain_actions.shape[1] >= 2:
        ax = axes[0, 1]
        ax.plot(times, brain_actions[:, 0], 'b-', label='Forward', linewidth=1.5)
        ax.plot(times, brain_actions[:, 1], 'r-', label='Turn', linewidth=1.5)
        ax.axhline(0, color='k', linestyle='-', alpha=0.3)
        ax.set_ylabel('Command [-1, 1]')
        ax.set_title('Brain Motor Output')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    # Odor concentration
    if odor_concs is not None:
        ax = axes[1, 0]
        ax.plot(times, odor_concs, 'g-', linewidth=1)
        ax.fill_between(times, 0, odor_concs, alpha=0.3, color='g')
        ax.set_ylabel('Concentration')
        ax.set_title('Odor Field Gradient')
        ax.grid(True, alpha=0.3)
    
    # Joint angles (femur)
    if joint_angles is not None and joint_angles.shape[1] >= 42:
        ax = axes[1, 1]
        femur_cols = [3, 10, 17, 24, 31, 38]
        femur_data = joint_angles[:, femur_cols]
        
        for i, col in enumerate(femur_cols):
            ax.plot(times, femur_data[:, i], alpha=0.6, linewidth=1, label=f'Leg {i+1}')
        
        ax.axhline(-1.5, color='r', linestyle='--', alpha=0.5, label='Min valid')
        ax.axhline(-0.2, color='r', linestyle='--', alpha=0.5)
        ax.set_ylabel('Angle (rad)')
        ax.set_title('Femur Joint Angles')
        ax.legend(loc='right', fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save
    plot_path = output_dir / "analysis_plots.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved plots: {plot_path}")
    
    return plot_path


def main():
    """Main analysis routine."""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python tools/analyze_enhanced.py <path_to_simulation_data.pkl>")
        print("\nExample:")
        print("  python tools/analyze_enhanced.py outputs/simulations/physics_3d/2026-03-12_21_45/simulation_data.pkl")
        sys.exit(1)
    
    pkl_path = sys.argv[1]
    
    # Load data
    data = load_pickle_data(pkl_path)
    if data is None:
        sys.exit(1)
    
    # Analyze
    analyze_trajectory_data(data, pkl_path)
    
    # Create plots
    try:
        plot_path = create_analysis_plots(data, pkl_path)
        print(f"\n✓ Analysis complete!")
    except Exception as e:
        print(f"\nWarning: Could not create plots: {e}")
    
    plt.show()


if __name__ == "__main__":
    main()
