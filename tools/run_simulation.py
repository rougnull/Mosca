#!/usr/bin/env python3
"""
Run olfactory navigation simulation with automatic timestamped output.

Creates outputs/YYYY-MM-DD_HH-MM-SS/ directory and saves:
- trajectory.csv (full simulation data)
- simulation.mp4 (rendered video)
- config.json (simulation parameters)

Usage:
    python tools/run_simulation.py \
        --mode gradient \
        --sigma 15.0 \
        --threshold 0.1 \
        --duration 10 \
        --output-dir outputs

Default: Creates timestamped subfolder automatically
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import csv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain
from controllers.brain_fly import BrainFly
from simulation.olfactory_sim import OlfactorySimulation


def create_timestamped_output_dir(base_dir):
    """Create outputs/YYYY-MM-DD_HH-MM-SS directory."""
    base_dir = Path(base_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sim_dir = base_dir / timestamp
    sim_dir.mkdir(parents=True, exist_ok=True)
    return sim_dir


def run_simulation_simple(
    mode="gradient",
    sigma=15.0,
    threshold=0.1,
    forward_scale=1.0,
    turn_scale=1.0,
    duration=5.0,
    arena_size=(100, 100, 10),
    source_pos=(50, 50, 5),
    output_dir="outputs",
    render_video=True,
    fps=30,
):
    """
    Run simple olfactory navigation simulation with trajectory logging.
    
    Args:
        mode: "binary", "gradient", or "temporal_gradient"
        sigma: Odor field width (mm)
        threshold: Brain activation threshold
        forward_scale: Maximum forward velocity
        turn_scale: Maximum turn velocity
        duration: Simulation duration (seconds)
        arena_size: Arena dimensions (x, y, z) in mm
        source_pos: Odor source position (x, y, z) in mm
        output_dir: Base output directory
        render_video: Whether to render MP4
        fps: Video FPS
    
    Returns:
        Path to output directory
    """
    
    # Create timestamped output directory
    sim_dir = create_timestamped_output_dir(output_dir)
    
    print(f"\n{'='*60}")
    print(f"OLFACTORY NAVIGATION SIMULATION")
    print(f"{'='*60}")
    print(f"Output: {sim_dir}")
    print(f"\nParameters:")
    print(f"  Mode: {mode}")
    print(f"  Sigma: {sigma} mm")
    print(f"  Threshold: {threshold}")
    print(f"  Duration: {duration} s")
    print(f"  Arena: {arena_size[0]}×{arena_size[1]}×{arena_size[2]} mm")
    print(f"  Source: ({source_pos[0]}, {source_pos[1]}, {source_pos[2]}) mm")
    
    # Create odor field
    print(f"\nInitializing odor field...")
    odor_field = OdorField(
        sources=[tuple(source_pos[:2])],
        sigma=sigma,
        amplitude=1.0
    )
    
    # Create brain
    print(f"Initializing olfactory brain ({mode} mode)...")
    brain = OlfactoryBrain(
        mode=mode,
        threshold=threshold,
        forward_scale=forward_scale,
        turn_scale=turn_scale,
    )
    
    # Create BrainFly (NOTE: requires FlyGym)
    print(f"Initializing BrainFly...")
    try:
        brain_fly = BrainFly(
            brain=brain,
            odor_field=odor_field,
            name="Nuro"
        )
    except Exception as e:
        print(f"WARNING: BrainFly initialization failed: {e}")
        print(f"  (FlyGym may not be available, using simple simulation)")
        brain_fly = None
    
    # Create simulation
    print(f"Initializing simulation...")
    use_simple = brain_fly is None
    
    if not use_simple:
        try:
            sim = OlfactorySimulation(
                brain_fly=brain_fly,
                odor_field=odor_field,
                output_dir=str(sim_dir)
            )
            
            # Setup with arena parameters
            sim.setup(arena_size=arena_size, use_rendering=False)
            
        except Exception as e:
            print(f"ERROR: FlyGym simulation setup failed: {e}")
            print(f"  Falling back to simple simulation...")
            use_simple = True
    
    if use_simple:
        print(f"  Using simple (non-physics) simulation...")
        simple_sim_path = Path(__file__).parent / "simple_olfactory_sim.py"
        spec = __import__('importlib.util').util.spec_from_file_location("simple_olfactory_sim", simple_sim_path)
        simple_mod = __import__('importlib.util').util.module_from_spec(spec)
        spec.loader.exec_module(simple_mod)
        SimpleOlfactorySim = simple_mod.SimpleOlfactorySim
        sim = SimpleOlfactorySim(odor_field, brain, source_pos, arena_size)
    
    # Run simulation
    print(f"\nRunning simulation for {duration} seconds...")
    try:
        if use_simple:
            # Simple simulation
            sim.run(duration=duration, dt=0.01)
            
            # trajectory already logged in sim.times/positions/odor_concs
            traj = list(zip(sim.times, sim.positions, sim.odor_concs))
            
        else:
            # FlyGym simulation
            obs, info = sim.reset()
            n_steps = int(duration / sim.sim_params["control_dt"])
            traj = []
            
            for step_i in range(n_steps):
                if step_i % max(1, n_steps // 10) == 0:
                    print(f"  Step {step_i}/{n_steps}...")
                
                # Compute action
                action = sim.brain_fly.step(obs)
                
                # Step simulation
                obs, reward, terminated, truncated, info = sim.sim.step(action)
                
                # Log trajectory
                if hasattr(obs.get("Nuro", {}), "get"):
                    head_pos = obs["Nuro"].get("head_position", [0, 0, 0])
                else:
                    head_pos = [0, 0, 0]
                
                conc = odor_field.concentration_at(np.array(head_pos[:2]))
                
                traj.append((step_i * sim.sim_params["control_dt"], head_pos, conc))
                
                if terminated or truncated:
                    break
        
        print(f"  ✓ Completed {len(traj)} steps")
        
    except Exception as e:
        print(f"ERROR during simulation: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Save trajectory CSV
    csv_path = sim_dir / "trajectory.csv"
    print(f"\nSaving trajectory: {csv_path}")
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'x', 'y', 'z', 'conc', 'distance_to_source'])
        
        for t, pos, c in traj:
            # Ensure pos is iterable
            if hasattr(pos, '__len__'):
                x, y, z = pos[0], pos[1], pos[2] if len(pos) > 2 else 0
            else:
                x, y, z = 0, 0, 0
            
            dist = np.linalg.norm(np.array([x, y]) - np.array(source_pos[:2]))
            writer.writerow([t, x, y, z, c, dist])
    
    # Compute metrics
    if len(traj) > 0:
        positions = np.array([p[1] if hasattr(p[1], '__len__') else [0, 0, 0] for p in traj])
        odors = np.array([p[2] for p in traj])
        
        metrics = {
            "n_steps": len(traj),
            "duration": traj[-1][0] if traj else 0,
            "mean_odor": float(np.mean(odors)),
            "max_odor": float(np.max(odors)),
            "final_distance": float(np.linalg.norm(
                np.array(positions[-1, :2]) - np.array(source_pos[:2])
            )) if len(positions) > 0 else 0,
        }
    else:
        metrics = {
            "n_steps": 0,
            "duration": 0,
            "mean_odor": 0,
            "max_odor": 0,
            "final_distance": np.linalg.norm(np.array(source_pos[:2]) - np.array(source_pos[:2])),
        }
    
    # Print metrics
    print(f"\nSimulation Results:")
    for key, val in metrics.items():
        if isinstance(val, float):
            print(f"  {key}: {val:.4f}")
        else:
            print(f"  {key}: {val}")
    
    # Save configuration
    config = {
        "mode": mode,
        "sigma": sigma,
        "threshold": threshold,
        "forward_scale": forward_scale,
        "turn_scale": turn_scale,
        "duration": duration,
        "arena_size": arena_size,
        "source_pos": source_pos,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
    }
    
    config_path = sim_dir / "config.json"
    print(f"\nSaving configuration: {config_path}")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Render video if requested and CSV exists
    if render_video and csv_path.exists():
        print(f"\nRendering video...")
        try:
            # Import video renderer dynamically
            render_path = Path(__file__).parent / "render_simulation_video.py"
            spec = __import__('importlib.util').util.spec_from_file_location("render_sim_video", render_path)
            render_mod = __import__('importlib.util').util.module_from_spec(spec)
            spec.loader.exec_module(render_mod)
            SimulationVideoRenderer = render_mod.SimulationVideoRenderer
            
            renderer = SimulationVideoRenderer(
                csv_path=str(csv_path),
                arena_size=arena_size[:2],
                sigma=sigma,
                source_pos=source_pos[:2],
                fps=fps,
            )
            
            video_path = sim_dir / "simulation.mp4"
            renderer.render(str(video_path))
            
        except Exception as e:
            print(f"  WARNING: Video rendering failed: {e}")
            print(f"  (Video generation can be retried manually)")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"✓ Simulation complete!")
    try:
        print(f"✓ Output directory: {sim_dir.relative_to(Path.cwd())}")
    except ValueError:
        print(f"✓ Output directory: {sim_dir}")
    print(f"{'='*60}\n")
    
    return sim_dir


def main():
    parser = argparse.ArgumentParser(
        description="Run olfactory navigation simulation with video rendering"
    )
    
    # Brain parameters
    parser.add_argument('--mode', type=str, default='gradient',
                       choices=['binary', 'gradient', 'temporal_gradient'],
                       help='OlfactoryBrain mode')
    parser.add_argument('--threshold', type=float, default=0.1,
                       help='Brain activation threshold')
    parser.add_argument('--forward-scale', type=float, default=1.0,
                       help='Maximum forward velocity')
    parser.add_argument('--turn-scale', type=float, default=1.0,
                       help='Maximum turn velocity')
    
    # Odor field parameters
    parser.add_argument('--sigma', type=float, default=15.0,
                       help='Odor field Gaussian sigma (mm)')
    parser.add_argument('--source-x', type=float, default=50.0,
                       help='Source X position (mm)')
    parser.add_argument('--source-y', type=float, default=50.0,
                       help='Source Y position (mm)')
    parser.add_argument('--source-z', type=float, default=5.0,
                       help='Source Z position (mm)')
    
    # Simulation parameters
    parser.add_argument('--duration', type=float, default=5.0,
                       help='Simulation duration (seconds)')
    parser.add_argument('--arena-x', type=float, default=100.0,
                       help='Arena X size (mm)')
    parser.add_argument('--arena-y', type=float, default=100.0,
                       help='Arena Y size (mm)')
    parser.add_argument('--output-dir', type=str, default='outputs',
                       help='Base output directory (timestamped subdirs auto-created)')
    
    # Video parameters
    parser.add_argument('--no-video', action='store_true',
                       help='Skip video rendering')
    parser.add_argument('--fps', type=int, default=30,
                       help='Video FPS')
    
    args = parser.parse_args()
    
    # Run simulation
    sim_dir = run_simulation_simple(
        mode=args.mode,
        sigma=args.sigma,
        threshold=args.threshold,
        forward_scale=args.forward_scale,
        turn_scale=args.turn_scale,
        duration=args.duration,
        arena_size=(args.arena_x, args.arena_y, 10),
        source_pos=(args.source_x, args.source_y, args.source_z),
        output_dir=args.output_dir,
        render_video=not args.no_video,
        fps=args.fps,
    )
    
    return sim_dir


if __name__ == '__main__':
    main()
