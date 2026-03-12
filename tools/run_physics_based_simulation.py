#!/usr/bin/env python3
"""
Physics-Based 3D Simulation with FlyGym
========================================

CRITICAL DIFFERENCE from run_complete_3d_simulation.py:
This version uses FlyGym's physics engine FROM THE START instead of
kinematic simulation. This ensures:
- Proper ground contact and collision detection
- Realistic body dynamics and balance
- Physics-valid joint angles at all times
- No Z-constant or rotation issues

PIPELINE:
1. Initialize FlyGym Simulation with physics
2. Use BrainFly + ImprovedOlfactoryBrain for control
3. Execute physics simulation steps
4. Record and render directly from physics simulation

USAGE:
    python tools/run_physics_based_simulation.py [--duration 5] [--seed 42]

OUTPUT:
    - outputs/simulations/physics_3d/{timestamp}/simulation_video.mp4
    - outputs/simulations/physics_3d/{timestamp}/simulation_data.pkl
"""

import sys
from pathlib import Path
import pickle
from datetime import datetime
import argparse

# Try to import tqdm for progress bars (optional)
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = None

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Try to import FlyGym components
try:
    from flygym import Fly, Camera, SingleFlySimulation
    from flygym.arena import FlatTerrain
    from flygym.preprogrammed import all_leg_dofs
    import numpy as np

    # Import project components (also require numpy)
    from olfaction.odor_field import OdorField
    from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain
    from controllers.brain_fly import BrainFly

    HAS_FLYGYM = True
except ImportError as e:
    print(f"Error: Required dependencies not available: {e}")
    print("\nThis script requires:")
    print("  - FlyGym: pip install flygym")
    print("  - NumPy: pip install numpy")
    print("\nInstall all dependencies with:")
    print("  pip install flygym numpy")
    HAS_FLYGYM = False
    np = None
    OdorField = None
    ImprovedOlfactoryBrain = None
    BrainFly = None


class PhysicsBasedOlfactorySimulation:
    """
    Complete physics-based olfactory navigation simulation.

    Unlike the kinematic version, this uses FlyGym's MuJoCo physics
    engine from the start, ensuring realistic movement.
    """

    def __init__(
        self,
        odor_source=(50.0, 50.0, 5.0),
        odor_sigma=8.0,
        odor_amplitude=100.0,
        start_pos=(35.0, 35.0, 3.0),
        sim_duration=5.0,
        timestep=1e-4,
        render_fps=30,
        seed=42,
        enable_rendering=False
    ):
        """
        Initialize physics-based simulation.

        Parameters
        ----------
        odor_source : tuple
            Odor source position (x, y, z) in mm
        odor_sigma : float
            Gaussian width of odor plume (mm)
        odor_amplitude : float
            Maximum odor concentration at source
        start_pos : tuple
            Starting position (x, y, z) in mm
        sim_duration : float
            Total simulation time (seconds)
        timestep : float
            Physics timestep (seconds, default 1e-4 = 0.1ms)
        render_fps : int
            Video frame rate (Hz)
        seed : int
            Random seed
        enable_rendering : bool
            Whether to enable video rendering (default: False)
            Set to False to run simulation without camera (faster)
        """
        if not HAS_FLYGYM:
            raise RuntimeError("FlyGym is required but not installed")

        np.random.seed(seed)

        self.sim_duration = sim_duration
        self.timestep = timestep
        self.render_fps = render_fps
        self.render_interval = int(1.0 / (render_fps * timestep))
        self.enable_rendering = enable_rendering

        # Create odor field
        self.odor_field = OdorField(
            sources=odor_source,
            sigma=odor_sigma,
            amplitude=odor_amplitude
        )

        # Create brain
        self.brain = ImprovedOlfactoryBrain(
            bilateral_distance=1.2,
            forward_scale=1.0,
            turn_scale=0.8,
            temporal_gradient_gain=10.0
        )

        # Create BrainFly (inherits from Fly, integrates brain + odor sensing)
        self.fly = BrainFly(
            brain=self.brain,
            odor_field=self.odor_field,
            init_pose="stretch",
            actuated_joints=all_leg_dofs,  # All 42 DoF
            control="position",  # Position control (absolute angles)
            spawn_pos=start_pos,
            motor_mode="direct_joints",  # Use CPG to convert to 42 DoF
            enable_adhesion=True,  # Enable tarsal adhesion for proper ground contact
        )

        # Create simulation with physics
        # Note: Camera is optional - only add if rendering is enabled
        sim_kwargs = {
            "fly": self.fly,
            "arena": FlatTerrain(),
            "timestep": timestep,
        }

        if enable_rendering:
            # Camera configuration for FlyGym
            # Using fly-attached camera as per FlyGym documentation
            try:
                camera = Camera(
                    fly=self.fly,
                    camera_id="Animat/camera_left",  # Standard FlyGym camera mount
                    play_speed=0.1,
                    fps=render_fps,
                )
                sim_kwargs["cameras"] = [camera]
                print("[INFO] Rendering enabled with camera")
            except Exception as e:
                print(f"[WARNING] Could not initialize camera: {e}")
                print("[INFO] Continuing without camera (rendering disabled)")
                self.enable_rendering = False
        else:
            print("[INFO] Rendering disabled - running physics simulation only")

        self.sim = SingleFlySimulation(**sim_kwargs)

        # Storage for trajectory data
        self.trajectory_data = {
            "times": [],
            "positions": [],
            "headings": [],
            "orientations": [],
            "odor_concentrations": [],
            "brain_actions": [],
            "joint_angles": [],
            "contact_forces": [],
        }

        # Initialize simulation
        self.obs, self.info = self.sim.reset(seed=seed)

        print("\n" + "="*70)
        print("PHYSICS-BASED OLFACTORY SIMULATION")
        print("="*70)
        print(f"Duration: {sim_duration}s")
        print(f"Physics timestep: {timestep}s")
        print(f"Odor source: {odor_source}, sigma={odor_sigma}mm, A={odor_amplitude}")
        print(f"Start pos: {start_pos}")
        print(f"Render FPS: {render_fps}")
        print(f"Total steps: {int(sim_duration / timestep)}")

    def step(self) -> bool:
        """
        Execute one simulation step with physics.

        Returns
        -------
        bool
            True if simulation should continue
        """
        # Get action from BrainFly based on current observations
        action = self.fly.step(self.obs)

        # Execute physics step
        self.obs, reward, terminated, truncated, self.info = self.sim.step(action)

        # Extract position and heading from observations
        if "fly" in self.obs:
            position = self.obs["fly"][0]  # [x, y, z]
            orientation = self.obs["fly"][2]  # [roll, pitch, yaw]
            heading = orientation[2]  # yaw
        else:
            position = np.zeros(3)
            orientation = np.zeros(3)
            heading = 0.0

        # Get odor concentration at current position
        conc = float(self.odor_field.concentration_at(position))

        # Get brain action
        brain_action = [action.get("joints", np.zeros(2))[0] if len(action.get("joints", [])) < 3 else 0.0,
                        action.get("joints", np.zeros(2))[1] if len(action.get("joints", [])) < 3 else 0.0]

        # Store data
        current_time = len(self.trajectory_data["times"]) * self.timestep
        self.trajectory_data["times"].append(current_time)
        self.trajectory_data["positions"].append(position.copy())
        self.trajectory_data["headings"].append(heading)
        self.trajectory_data["orientations"].append(orientation.copy())
        self.trajectory_data["odor_concentrations"].append(conc)
        self.trajectory_data["brain_actions"].append(brain_action)

        if "joints" in self.obs:
            self.trajectory_data["joint_angles"].append(self.obs["joints"][0].copy())  # Angles only
        else:
            self.trajectory_data["joint_angles"].append(np.zeros(42))

        if "contact_forces" in self.obs:
            self.trajectory_data["contact_forces"].append(self.obs["contact_forces"].copy())

        # Check termination
        if terminated or truncated:
            return False

        return True

    def run(self, save_video=True) -> bool:
        """
        Run complete simulation.

        Parameters
        ----------
        save_video : bool
            Whether to save video frames (only works if rendering is enabled)

        Returns
        -------
        bool
            True if successful
        """
        print(f"\n[1/2] Running physics simulation...")

        n_steps = int(self.sim_duration / self.timestep)
        video_frames = []

        # Only save video if rendering is enabled
        should_render = save_video and self.enable_rendering

        if HAS_TQDM:
            # Use tqdm progress bar if available
            with tqdm(total=n_steps, desc="  Simulating") as pbar:
                for step_idx in range(n_steps):
                    if not self.step():
                        print(f"  [!] Simulation terminated early at step {step_idx}")
                        break

                    # Render frame if needed
                    if should_render and (step_idx % self.render_interval == 0):
                        try:
                            rendered = self.sim.render()
                            if rendered and len(rendered) > 0:
                                frame = rendered[0]  # Get first camera
                                if frame is not None:
                                    video_frames.append(frame)
                        except Exception as e:
                            if step_idx == 0:  # Only warn on first failure
                                print(f"  [!] Rendering failed: {e}")
                                should_render = False  # Disable further rendering attempts

                    pbar.update(1)
        else:
            # Fallback: print progress at intervals
            print(f"  Simulating {n_steps} steps...")
            progress_interval = max(1, n_steps // 20)  # Print 20 updates
            for step_idx in range(n_steps):
                if not self.step():
                    print(f"  [!] Simulation terminated early at step {step_idx}")
                    break

                # Render frame if needed
                if should_render and (step_idx % self.render_interval == 0):
                    try:
                        rendered = self.sim.render()
                        if rendered and len(rendered) > 0:
                            frame = rendered[0]  # Get first camera
                            if frame is not None:
                                video_frames.append(frame)
                    except Exception as e:
                        if step_idx == 0:  # Only warn on first failure
                            print(f"  [!] Rendering failed: {e}")
                            should_render = False  # Disable further rendering attempts

                # Print progress updates
                if step_idx % progress_interval == 0 or step_idx == n_steps - 1:
                    percent = (step_idx + 1) / n_steps * 100
                    print(f"  Progress: {percent:.1f}% ({step_idx + 1}/{n_steps} steps)")

        print("  [OK] Simulation completed")

        # Save video if frames were collected
        if should_render and len(video_frames) > 0:
            self.video_frames = video_frames
            print(f"  [OK] Collected {len(video_frames)} video frames")
        elif save_video and not self.enable_rendering:
            print("  [INFO] Video not saved - rendering was disabled")

        return True

    def save_data(self, output_dir: Path = None) -> Path:
        """
        Save trajectory data and video.

        Parameters
        ----------
        output_dir : Path
            Output directory (auto-generated if None)

        Returns
        -------
        Path
            Path to output directory
        """
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M")
            output_dir = PROJECT_ROOT / "outputs" / "simulations" / "physics_3d" / timestamp

        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert lists to arrays
        for key in ["times", "positions", "headings", "orientations",
                    "odor_concentrations", "brain_actions", "joint_angles"]:
            self.trajectory_data[key] = np.array(self.trajectory_data[key])

        # Save trajectory data
        data_file = output_dir / "simulation_data.pkl"
        with open(data_file, "wb") as f:
            pickle.dump(self.trajectory_data, f)
        print(f"\n  [OK] Saved data: {data_file}")

        # Save video if available
        if hasattr(self, "video_frames") and len(self.video_frames) > 0:
            try:
                import cv2
                video_file = output_dir / "simulation_video.mp4"

                # Get frame dimensions
                height, width, _ = self.video_frames[0].shape

                # Create video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(str(video_file), fourcc, self.render_fps,
                                     (width, height))

                for frame in self.video_frames:
                    # Convert RGB to BGR for cv2
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    out.write(frame_bgr)

                out.release()
                print(f"  [OK] Saved video: {video_file}")

            except ImportError:
                print("  [!] opencv-python not available, skipping video save")
                print("      Install with: pip install opencv-python")

        return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Physics-based 3D olfactory simulation"
    )
    parser.add_argument("--duration", type=float, default=5.0,
                       help="Simulation duration in seconds (default: 5)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed (default: 42)")
    parser.add_argument("--enable-render", action="store_true",
                       help="Enable video rendering with camera (slower, may cause errors if camera setup fails)")
    parser.add_argument("--no-video", action="store_true",
                       help="Skip video recording (only applies if --enable-render is used)")
    args = parser.parse_args()

    if not HAS_FLYGYM:
        print("\n[ERROR] Required dependencies are not installed")
        print("\nThis script requires:")
        print("  - FlyGym: pip install flygym")
        print("  - NumPy: pip install numpy")
        print("\nInstall all dependencies with:")
        print("  pip install flygym numpy")
        return False

    # Create and run simulation
    sim = PhysicsBasedOlfactorySimulation(
        odor_source=(50.0, 50.0, 5.0),
        odor_sigma=8.0,
        odor_amplitude=100.0,
        start_pos=(35.0, 35.0, 3.0),
        sim_duration=args.duration,
        timestep=1e-4,  # 0.1ms physics timestep
        render_fps=30,
        seed=args.seed,
        enable_rendering=args.enable_render
    )

    # Only try to save video if rendering is enabled
    save_video = args.enable_render and not args.no_video
    if not sim.run(save_video=save_video):
        print("\n[X] Simulation failed")
        return False

    # Save results
    output_dir = sim.save_data()

    print("\n" + "="*70)
    print("[OK] SIMULATION COMPLETED SUCCESSFULLY")
    print(f"  Output: {output_dir}")
    print("="*70)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
