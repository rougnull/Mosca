#!/usr/bin/env python3
"""
Render MP4 video from olfactory navigation simulation trajectory.

Reads CSV trajectory file and creates 2D/3D visualization with:
- Fly path overlay
- Odor concentration field (heatmap)
- Brain state indicators
- Real-time metrics

Usage:
    python tools/render_simulation_video.py \
        --csv outputs/2026-03-12_14-30-45/trajectory.csv \
        --output outputs/2026-03-12_14-30-45/simulation.mp4 \
        --sigma 15.0 \
        --fps 30
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.colors import Normalize
import sys


class SimulationVideoRenderer:
    """Render simulation trajectory to MP4 video."""
    
    def __init__(self, csv_path, arena_size=(100, 100), sigma=15.0, 
                 source_pos=(50, 50), fps=30, dpi=100):
        """
        Initialize renderer.
        
        Args:
            csv_path: Path to trajectory CSV
            arena_size: Arena dimensions (x, y) in mm
            sigma: Odor field Gaussian sigma
            source_pos: Odor source location (x, y)
            fps: Frames per second
            dpi: Figure DPI
        """
        self.csv_path = Path(csv_path)
        self.arena_size = arena_size
        self.sigma = sigma
        self.source_pos = np.array(source_pos)
        self.fps = fps
        self.dpi = dpi
        
        # Load trajectory
        print(f"Loading trajectory from {csv_path}...")
        self.traj = pd.read_csv(csv_path)
        self.n_frames = len(self.traj)
        
        print(f"  Loaded {self.n_frames} frames")
        print(f"  Duration: {self.traj['timestamp'].iloc[-1]:.2f} s")
        print(f"  Arena: {arena_size[0]}×{arena_size[1]} mm")
        print(f"  Source: {source_pos}")
        
        # Precompute odor field grid
        self._precompute_odor_field()
        
    def _precompute_odor_field(self):
        """Precompute gaussian odor field on grid."""
        # Create grid
        x = np.linspace(0, self.arena_size[0], 50)
        y = np.linspace(0, self.arena_size[1], 50)
        X, Y = np.meshgrid(x, y)
        
        # Compute gaussian
        dist_sq = (X - self.source_pos[0])**2 + (Y - self.source_pos[1])**2
        self.odor_grid = np.exp(-dist_sq / (2 * self.sigma**2))
        self.X = X
        self.Y = Y
        
    def _create_figure(self):
        """Create matplotlib figure with subplots."""
        fig = plt.figure(figsize=(14, 6), dpi=self.dpi)
        
        # Left: Arena with path
        self.ax_arena = fig.add_subplot(121)
        
        # Right: Metrics over time
        self.ax_metrics = fig.add_subplot(222)
        self.ax_metrics.set_xlabel("Time (s)")
        self.ax_metrics.set_ylabel("Distance to source (mm)")
        self.ax_metrics.grid(True, alpha=0.3)
        
        # Bottom right: Concentration trace
        self.ax_conc = fig.add_subplot(224)
        self.ax_conc.set_xlabel("Time (s)")
        self.ax_conc.set_ylabel("Odor conc")
        self.ax_conc.grid(True, alpha=0.3)
        
        fig.tight_layout()
        return fig
        
    def _setup_arena_plot(self):
        """Setup arena subplot."""
        ax = self.ax_arena
        ax.set_xlim(0, self.arena_size[0])
        ax.set_ylim(0, self.arena_size[1])
        ax.set_aspect('equal')
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        ax.set_title("Simulation Arena - Fly Trajectory & Odor Field")
        
        # Draw odor field (low contrast)
        im = ax.contourf(self.X, self.Y, self.odor_grid, levels=15, 
                         cmap='YlOrRd', alpha=0.6)
        plt.colorbar(im, ax=ax, label="Conc")
        
        # Source marker
        ax.plot(*self.source_pos, 'r*', markersize=20, 
                label='Odor Source', zorder=10)
        
        # Trajectory line (will be updated)
        self.line_path, = ax.plot([], [], 'b-', linewidth=1.5, 
                                  alpha=0.7, label='Path')
        
        # Current position marker
        self.marker_fly, = ax.plot([], [], 'bo', markersize=8, 
                                   label='Fly', zorder=9)
        
        ax.legend(loc='upper left')
        
    def render(self, output_path, max_frames=None):
        """
        Render simulation to MP4 video.
        
        Args:
            output_path: Output video file path
            max_frames: Limit frames (None = all)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Limit frames if requested
        n_frames = min(self.n_frames, max_frames) if max_frames else self.n_frames
        
        # Create figure
        fig = self._create_figure()
        self._setup_arena_plot()
        
        # Setup writer
        writer = FFMpegWriter(fps=self.fps, bitrate=1800)
        
        print(f"\nRendering {n_frames} frames to {output_path}...")
        
        def animate(frame_idx):
            if frame_idx % max(1, n_frames // 10) == 0:
                print(f"  Frame {frame_idx}/{n_frames}...", end='\r')
            
            # Get current state
            t = self.traj['timestamp'].iloc[frame_idx]
            x = self.traj['x'].iloc[frame_idx]
            y = self.traj['y'].iloc[frame_idx]
            conc = self.traj['conc'].iloc[frame_idx]
            dist = self.traj['distance_to_source'].iloc[frame_idx]
            
            # Update arena plot
            # Path up to current frame
            path_x = self.traj['x'].iloc[:frame_idx+1].values
            path_y = self.traj['y'].iloc[:frame_idx+1].values
            self.line_path.set_data(path_x, path_y)
            
            # Current fly position
            self.marker_fly.set_data([x], [y])
            
            # Update metrics plot
            self.ax_metrics.clear()
            time_to_frame = self.traj['timestamp'].iloc[:frame_idx+1].values
            dist_to_frame = self.traj['distance_to_source'].iloc[:frame_idx+1].values
            self.ax_metrics.plot(time_to_frame, dist_to_frame, 'b-', alpha=0.7)
            self.ax_metrics.axhline(y=dist, color='r', linestyle='--', alpha=0.5)
            self.ax_metrics.set_xlabel("Time (s)")
            self.ax_metrics.set_ylabel("Distance to source (mm)")
            self.ax_metrics.grid(True, alpha=0.3)
            self.ax_metrics.set_ylim(0, max(dist_to_frame.max(), 50))
            
            # Update concentration plot
            self.ax_conc.clear()
            self.ax_conc.plot(time_to_frame, self.traj['conc'].iloc[:frame_idx+1].values, 
                            'orange', alpha=0.7)
            self.ax_conc.axhline(y=conc, color='r', linestyle='--', alpha=0.5)
            self.ax_conc.set_xlabel("Time (s)")
            self.ax_conc.set_ylabel("Odor concentration")
            self.ax_conc.grid(True, alpha=0.3)
            self.ax_conc.set_ylim(0, 1.0)
            
            # Title with current metrics
            fig.suptitle(
                f"t={t:.2f}s | Position=({x:.1f}, {y:.1f}) mm | "
                f"Conc={conc:.4f} | Dist={dist:.1f} mm",
                fontsize=12, y=0.98
            )
            
        # Render animation
        with writer.saving(fig, str(output_path), dpi=self.dpi):
            for i in range(n_frames):
                animate(i)
                writer.grab_frame()
        
        print(f"\n✓ Video saved: {output_path}")
        print(f"  Duration: {n_frames / self.fps:.2f} seconds")
        print(f"  Dimensions: {int(fig.get_figwidth()*self.dpi)}x{int(fig.get_figheight()*self.dpi)} px")
        
        plt.close(fig)
        
    @staticmethod
    def render_all_in_directory(output_dir, pattern="trajectory.csv"):
        """
        Render all simulation CSVs in directory tree.
        
        Args:
            output_dir: Root output directory
            pattern: CSV filename pattern to look for
        """
        output_dir = Path(output_dir)
        csv_files = list(output_dir.rglob(pattern))
        
        print(f"Found {len(csv_files)} trajectory files")
        
        for csv_path in csv_files:
            output_video = csv_path.parent / "simulation.mp4"
            
            if output_video.exists():
                print(f"Skipping (video exists): {csv_path.parent.name}")
                continue
            
            try:
                renderer = SimulationVideoRenderer(csv_path)
                renderer.render(output_video)
            except Exception as e:
                print(f"ERROR rendering {csv_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Render olfactory navigation simulation to MP4 video"
    )
    parser.add_argument('--csv', type=str, required=True,
                       help='Path to trajectory CSV file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output MP4 path (default: same dir as CSV)')
    parser.add_argument('--sigma', type=float, default=15.0,
                       help='Odor field sigma (mm)')
    parser.add_argument('--source-x', type=float, default=50.0,
                       help='Odor source X position (mm)')
    parser.add_argument('--source-y', type=float, default=50.0,
                       help='Odor source Y position (mm)')
    parser.add_argument('--arena-x', type=float, default=100.0,
                       help='Arena X size (mm)')
    parser.add_argument('--arena-y', type=float, default=100.0,
                       help='Arena Y size (mm)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Video frames per second')
    parser.add_argument('--max-frames', type=int, default=None,
                       help='Limit rendering to N frames (for testing)')
    parser.add_argument('--dpi', type=int, default=100,
                       help='Figure DPI')
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output is None:
        csv_path = Path(args.csv)
        args.output = str(csv_path.parent / "simulation.mp4")
    
    # Render
    renderer = SimulationVideoRenderer(
        csv_path=args.csv,
        arena_size=(args.arena_x, args.arena_y),
        sigma=args.sigma,
        source_pos=(args.source_x, args.source_y),
        fps=args.fps,
        dpi=args.dpi
    )
    
    renderer.render(args.output, max_frames=args.max_frames)


if __name__ == '__main__':
    main()
