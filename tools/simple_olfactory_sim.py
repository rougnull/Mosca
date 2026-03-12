#!/usr/bin/env python3
"""
Pure simulation (no FlyGym required) for trajectory generation and video rendering.

UPDATED (2026-03-12): Now uses ImprovedOlfactoryBrain with TEMPORAL GRADIENT
for forward motion control to prevent overshooting at odor source.

Simulates simplified fly navigation in odor field without physics engine.
Useful for demonstrating video pipeline when FlyGym is not available.
"""

import numpy as np
from pathlib import Path
from datetime import datetime
import csv
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain


class SimpleOlfactorySim:
    """Simplified olfactory simulation without FlyGym physics."""
    
    def __init__(self, odor_field, brain, source_pos, arena_size=(100, 100, 10)):
        self.odor_field = odor_field
        self.brain = brain
        self.source_pos = np.array(source_pos)
        self.arena_size = arena_size
        
        # Start at position away from source
        self.pos = np.array([20.0, 20.0, 3.0])
        
        # Initial heading: face toward source
        to_source = self.source_pos[:2] - self.pos[:2]
        self.heading = np.arctan2(to_source[1], to_source[0])
        
        self.vel = np.array([0.0, 0.0, 0.0])
        
        # Logging
        self.times = []
        self.positions = []
        self.odor_concs = []
        self.actions = []
        
    def step(self, dt=0.01):
        """
        Execute one simulation step using IMPROVED bilateral gradient brain.
        
        Uses ImprovedOlfactoryBrain which:
        - Senses bilateral (left/right) gradients for turning
        - Uses temporal (d/dt) concentration change for forward motion
        - Prevents overshooting at odor source
        """
        # Brain decides action based on bilateral sensing + temporal gradient
        # ImprovedOlfactoryBrain.step() needs position and heading
        action = self.brain.step(self.odor_field, self.pos, self.heading)
        forward, turn = action[0], action[1]
        
        # Get odor concentration at current position (for logging)
        conc = float(self.odor_field.concentration_at(self.pos))
        
        # Simple kinematics
        max_forward = 50.0  # mm/s
        max_turn = 300.0    # deg/s
        
        v_forward = forward * max_forward
        v_turn = turn * max_turn * np.pi / 180  # convert to rad/s
        
        # Update heading
        self.heading += v_turn * dt
        
        # Update position
        self.vel[0] = v_forward * np.cos(self.heading)
        self.vel[1] = v_forward * np.sin(self.heading)
        self.vel[2] = 0.0
        
        self.pos = self.pos + self.vel * dt
        
        # Boundary conditions (reflect)
        if self.pos[0] < 0: self.pos[0] = 0; self.heading = np.pi - self.heading
        if self.pos[0] > self.arena_size[0]: self.pos[0] = self.arena_size[0]; self.heading = np.pi - self.heading
        if self.pos[1] < 0: self.pos[1] = 0; self.heading = -self.heading
        if self.pos[1] > self.arena_size[1]: self.pos[1] = self.arena_size[1]; self.heading = -self.heading
        
        self.pos[2] = np.clip(self.pos[2], 0, self.arena_size[2])
        
        # Log
        self.times.append(len(self.times) * dt)
        self.positions.append(self.pos.copy())
        self.odor_concs.append(conc)
        self.actions.append(action.copy())
        
        return conc
    
    def run(self, duration=10.0, dt=0.01):
        """Run simulation."""
        n_steps = int(duration / dt)
        for i in range(n_steps):
            self.step(dt)
            if i % 100 == 0:
                print(f"  Step {i}/{n_steps}...")
    
    def save_csv(self, filepath):
        """Save trajectory to CSV."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'x', 'y', 'z', 'conc', 'distance_to_source'])
            
            for t, pos, conc in zip(self.times, self.positions, self.odor_concs):
                dist = np.linalg.norm(pos[:2] - self.source_pos[:2])
                writer.writerow([t, pos[0], pos[1], pos[2], conc, dist])


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--sigma', type=float, default=15.0)
    parser.add_argument('--bilateral-distance', type=float, default=2.0)
    parser.add_argument('--forward-scale', type=float, default=0.5)
    parser.add_argument('--turn-scale', type=float, default=1.0)
    parser.add_argument('--duration', type=float, default=5.0)
    parser.add_argument('--output', type=str, default='trajectory.csv')
    
    args = parser.parse_args()
    
    # Create odor field
    odor_field = OdorField(sources=[(50.0, 50.0, 5.0)], sigma=args.sigma, amplitude=1.0)
    
    # Create IMPROVED brain with bilateral sensing + temporal gradient
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=args.bilateral_distance,
        forward_scale=args.forward_scale,
        turn_scale=args.turn_scale,
        threshold=0.0001,
    )
    
    # Run sim
    sim = SimpleOlfactorySim(odor_field, brain, source_pos=(50.0, 50.0, 5.0))
    print(f"Running {args.duration}s simulation (IMPROVED BRAIN with temporal gradient)...")
    sim.run(duration=args.duration)
    
    # Save
    sim.save_csv(args.output)
    print(f"Saved: {args.output}")

