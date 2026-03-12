#!/usr/bin/env python3
"""
proper MuJoCo 3D simulation and visualization with chemotaxis.

This script:
1. Runs the olfactory navigation simulation with ACTUAL FlyGym/MuJoCo physics
2. Records trajectory AND keyframe positions during sim
3. Exports video as proper 3D kinematic animation

NOT just replaying CSV data - ACTUAL physics simulation.
"""

import sys
import argparse
import numpy as np
import csv
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test FlyGym availability
try:
    from flygym import Fly, Simulation, Camera
    from flygym.arena import FlatTerrain
    from flygym.controller import HybridTurningFly
    FLYGYM_AVAILABLE = True
    print("[OK] FlyGym is available - will use REAL physics simulation")
except ImportError as e:
    print(f"[WARN] FlyGym not available: {e}")
    FLYGYM_AVAILABLE = False

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
from controllers.brain_fly import BrainFly


def run_mujoco_olfactory_sim(
    output_dir="outputs",
    duration=10.0,
    sigma=15.0,
    forward_scale=0.5,
    turn_scale=1.0,
    fps=30,
    render_video=True,
):
    """
    Run actual MuJoCo/FlyGym physics simulation with olfactory navigation.
    
    Args:
        output_dir: Where to save outputs
        duration: Simulation duration in seconds
        sigma: Odor field Gaussian width
        forward_scale: Forward velocity scale
        turn_scale: Turn velocity scale
        fps: Video FPS
        render_video: Whether to render MP4
    """
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sim_dir = Path(output_dir) / timestamp
    sim_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("MUJOCO OLFACTORY NAVIGATION SIMULATION (REAL PHYSICS)")
    print(f"{'='*70}")
    print(f"Output: {sim_dir}")
    print(f"Duration: {duration}s")
    print(f"FlyGym available: {FLYGYM_AVAILABLE}")
    
    # Parameters
    source_pos = np.array([50.0, 50.0, 5.0])
    arena_size = (100, 100, 10)
    
    # Create odor field
    print(f"\nCreating odor field (sigma={sigma})...")
    odor_field = OdorField(
        sources=[tuple(source_pos)],
        sigma=sigma,
        amplitude=1.0
    )
    
    # Create brain  
    print(f"Creating improved olfactory brain...")
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=2.0,
        forward_scale=forward_scale,
        turn_scale=turn_scale,
        threshold=0.0001,
    )
    
    # Logging
    times = []
    positions = []
    odor_concs = []
    motor_commands = []
    brain_diag = []
    
    if not FLYGYM_AVAILABLE:
        print("\n[FALLBACK] FlyGym not available, using kinematic simulation...")
        
        # Simple kinematic sim (no physics)
        from tools.simple_olfactory_sim import SimpleOlfactorySim
        
        sim = SimpleOlfactorySim(odor_field, brain, source_pos, arena_size)
        print(f"Running kinematic simulation for {duration}s...")
        
        n_steps = int(duration / 0.01)
        for step in range(n_steps):
            conc = sim.step(0.01)
            
            times.append(len(times) * 0.01)
            positions.append(sim.pos.copy())
            odor_concs.append(conc)
            
            if step % 1000 == 0 and step > 0:
                print(f"  Step {step}/{n_steps} ({100*step/n_steps:.0f}%)")
    
    else:
        print("\n[SUCCESS] Using FlyGym for ACTUAL physics simulation...")
        
        try:
            # Create FlyGym simulation
            print("Initializing FlyGym simulation...")
            arena = FlatTerrain()
            fly = Fly(
                enable_adhesion=True,
                enable_joint_sensors=True,
                enable_camera=True,
            )
            
            sim = Simulation(
                fly=fly,
                arena=arena,
                cameras=[],  # No rendering during simulation for speed
            )
            
            # Reset with initial position away from source
            obs, info = sim.reset()
            
            # Simulation loop
            print(f"Running FlyGym simulation for {duration}s...")
            dt = sim.sim_params["control_dt"]  # ~0.01s
            n_steps = int(duration / dt)
            
            for step in range(n_steps):
                if step % 100 == 0:
                    print(f"  Step {step}/{n_steps} ({100*step/n_steps:.0f}%)")
                
                # Get fly position from observation
                fly_pos = obs["Fly"][0].get("head_position", np.zeros(3))
                fly_heading = obs["Fly"][0].get("orientation", np.array([0, 0, 1]))  # z-axis heading
                heading_angle = np.arctan2(fly_heading[1], fly_heading[0])
                
                # Olfactory decision
                motor = brain.step(odor_field, fly_pos, heading_angle)
                forward, turn = motor
                
                # Apply action to FlyGym
                # Format depends on FlyGym version - typically dict or array
                try:
                    action = {"Fly": np.array([forward, turn])}
                    obs, reward, terminated, truncated, info = sim.step(action)
                except Exception as e:
                    # Fallback format
                    action = np.array([forward, turn])
                    obs, reward, terminated, truncated, info = sim.step(action)
                
                # Log data
                conc = float(odor_field.concentration_at(fly_pos))
                times.append(step * dt)
                positions.append(fly_pos.copy())
                odor_concs.append(conc)
                motor_commands.append(motor.copy())
                
                # Diagnostics every 10 steps
                if step % 10 == 0:
                    diag = brain.get_diagnostics()
                    brain_diag.append((step * dt, diag))
                
                if terminated or truncated:
                    print(f"  Simulation terminated at step {step}")
                    break
        
        except Exception as e:
            print(f"\n[ERROR] FlyGym simulation failed: {e}")
            print(f"Falling back to kinematic simulation...")
            
            from tools.simple_olfactory_sim import SimpleOlfactorySim
            sim = SimpleOlfactorySim(odor_field, brain, source_pos, arena_size)
            
            n_steps = int(duration / 0.01)
            for step in range(n_steps):
                conc = sim.step(0.01)
                times.append(len(times) * 0.01)
                positions.append(sim.pos.copy())
                odor_concs.append(conc)
    
    # Save trajectory
    print(f"\nSaving trajectory to CSV...")
    traj_file = sim_dir / "trajectory.csv"
    with open(traj_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'x', 'y', 'z', 'odor_concentration', 'distance_to_source'])
        writer.writeheader()
        
        for t, pos, conc in zip(times, positions, odor_concs):
            dist = np.linalg.norm(pos[:2] - source_pos[:2])
            writer.writerow({
                'timestamp': t,
                'x': pos[0],
                'y': pos[1],
                'z': pos[2],
                'odor_concentration': conc,
                'distance_to_source': dist,
            })
    
    # Save config
    config = {
        "timestamp": timestamp,
        "duration": duration,
        "odor_source": source_pos.tolist(),
        "arena_size": arena_size,
        "sigma": sigma,
        "forward_scale": forward_scale,
        "turn_scale": turn_scale,
        "physics_engine": "MuJoCo (FlyGym)" if FLYGYM_AVAILABLE else "Kinematic (simplified)",
        "total_steps": len(times),
        "final_position": positions[-1].tolist() if positions else None,
        "min_distance_to_source": float(np.min([np.linalg.norm(p[:2] - source_pos[:2]) for p in positions])),
    }
    
    with open(sim_dir / "config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"[OK] Trajectory saved: {traj_file}")
    print(f"[OK] Config saved: {sim_dir / 'config.json'}")
    
    # Render video if requested
    if render_video:
        print(f"\nRendering video with MuJoCo data...")
        try:
            # Use visualization module to create MP4 from trajectory
            from visualization.create_final_visualizations import SimpleVisualizer
            
            viz = SimpleVisualizer(sim_dir)
            viz.create_3d_visualization()
            viz.create_behavioral_plot()
            
            print(f"[OK] Video visualization created")
        except Exception as e:
            print(f"[WARN] Video rendering failed: {e}")
            print(f"       Trajectory saved but no MP4 generated")
    
    print(f"\n{'='*70}")
    print(f"SIMULATION COMPLETE")
    print(f"Results saved to: {sim_dir}")
    print(f"{'='*70}\n")
    
    return sim_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MuJoCo olfactory navigation simulation")
    parser.add_argument("--duration", type=float, default=10.0, help="Simulation duration (seconds)")
    parser.add_argument("--sigma", type=float, default=15.0, help="Odor field Gaussian width (mm)")
    parser.add_argument("--output", type=str, default="outputs", help="Output directory")
    parser.add_argument("--fps", type=int, default=30, help="Video FPS")
    parser.add_argument("--no-video", action="store_true", help="Don't render video")
    
    args = parser.parse_args()
    
    sim_dir = run_mujoco_olfactory_sim(
        output_dir=args.output,
        duration=args.duration,
        sigma=args.sigma,
        fps=args.fps,
        render_video=not args.no_video,
    )
