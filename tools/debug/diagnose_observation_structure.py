#!/usr/bin/env python3
"""
Diagnostic test to understand FlyGym observation structure.

This script initializes a FlyGym simulation and prints exactly what
observation structures are available, helping us understand where
joint angles are stored.
"""

import sys
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from flygym import Fly, SingleFlySimulation
    from flygym.arena import FlatTerrain
    from flygym.preprogrammed import all_leg_dofs
    HAS_FLYGYM = True
except ImportError as e:
    print(f"Error: FlyGym not installed: {e}")
    HAS_FLYGYM = False
    sys.exit(1)

def print_obs_structure(obs, prefix="", max_depth=3, current_depth=0):
    """Recursively print observation structure."""
    if current_depth >= max_depth:
        return
    
    indent = "  " * current_depth
    
    if isinstance(obs, dict):
        for key, value in obs.items():
            if isinstance(value, (dict, list, tuple)):
                print(f"{indent}[{key}] ({type(value).__name__})")
                print_obs_structure(value, prefix + f"[{key}]", max_depth, current_depth + 1)
            elif isinstance(value, np.ndarray):
                print(f"{indent}[{key}] (ndarray) shape={value.shape}, dtype={value.dtype}")
                if value.size <= 10:
                    print(f"{indent}  values: {value}")
            else:
                print(f"{indent}[{key}] ({type(value).__name__}) = {value}")
    
    elif isinstance(obs, (list, tuple)):
        for idx, item in enumerate(obs):
            if isinstance(item, (dict, list, tuple)):
                print(f"{indent}[{idx}] ({type(item).__name__})")
                print_obs_structure(item, prefix + f"[{idx}]", max_depth, current_depth + 1)
            elif isinstance(item, np.ndarray):
                print(f"{indent}[{idx}] (ndarray) shape={item.shape}, dtype={item.dtype}")
                if item.size <= 10:
                    print(f"{indent}  values: {item}")
            else:
                print(f"{indent}[{idx}] ({type(item).__name__}) = {item}")
    
    elif isinstance(obs, np.ndarray):
        print(f"{indent}(ndarray) shape={obs.shape}, dtype={obs.dtype}")
        if obs.size <= 20:
            print(f"{indent}values: {obs}")

def main():
    print("="*70)
    print("FLYGYM OBSERVATION STRUCTURE DIAGNOSTIC")
    print("="*70)
    
    # Create minimal FlyGym simulation
    print("\n[1] Initializing FlyGym simulation...")
    
    fly = Fly(enable_adhesion=True, enable_joint_sensors=True)
    arena = FlatTerrain()
    
    sim = SingleFlySimulation(
        fly=fly,
        arena=arena,
        timestep=1e-4,
    )
    
    print("[2] Resetting simulation...")
    obs, info = sim.reset()
    
    print("\n" + "="*70)
    print("OBSERVATION STRUCTURE AT RESET:")
    print("="*70)
    print_obs_structure(obs, max_depth=4)
    
    print("\n" + "="*70)
    print("INFO STRUCTURE AT RESET:")
    print("="*70)
    print_obs_structure(info, max_depth=3)
    
    print("\n" + "="*70)
    print("SIMULATION METADATA:")
    print("="*70)
    print(f"Fly class: {fly.__class__.__name__}")
    print(f"Fly actuated_joints: {len(fly.actuated_joints)} joints")
    print(f"Fly actuated_joints names: {fly.actuated_joints[:5]}... (showing first 5)")
    
    if hasattr(fly, 'dofs'):
        print(f"Fly dofs attribute: {fly.dofs[:5]}... (first 5)")
    
    print(f"\nSimulation class: {sim.__class__.__name__}")
    
    # Try taking a step to see if observation changes
    print("\n" + "="*70)
    print("AFTER ONE SIMULATION STEP:")
    print("="*70)
    
    action = np.zeros(len(fly.actuated_joints))
    obs, reward, terminated, truncated, info = sim.step(action)
    
    print("\nObservation keys after step:")
    if isinstance(obs, dict):
        for key in sorted(obs.keys()):
            val = obs[key]
            if isinstance(val, np.ndarray):
                print(f"  '{key}': ndarray shape={val.shape}, dtype={val.dtype}")
            elif isinstance(val, (list, tuple)):
                if len(val) > 0 and isinstance(val[0], np.ndarray):
                    print(f"  '{key}': list/tuple of {type(val[0]).__name__}, first shape={val[0].shape}")
                else:
                    print(f"  '{key}': list/tuple of length {len(val)}")
            else:
                print(f"  '{key}': {type(val).__name__}")
    
    print("\n" + "="*70)
    print("DETAILED OBSERVATION AFTER STEP:")
    print("="*70)
    print_obs_structure(obs, max_depth=3)
    
    # Try to find joint angles
    print("\n" + "="*70)
    print("SEARCHING FOR JOINT ANGLES:")
    print("="*70)
    
    def find_arrays_by_size(obj, target_size, path=""):
        """Find arrays with specific size."""
        results = []
        
        if isinstance(obj, np.ndarray):
            if obj.size == target_size:
                results.append((path, obj.shape, obj.dtype))
        elif isinstance(obj, dict):
            for key, val in obj.items():
                results.extend(find_arrays_by_size(val, target_size, f"{path}.{key}" if path else key))
        elif isinstance(obj, (list, tuple)):
            for idx, item in enumerate(obj):
                results.extend(find_arrays_by_size(item, target_size, f"{path}[{idx}]"))
        
        return results
    
    print(f"\nSearching for arrays with 42 elements (42 joint angles):")
    results_42 = find_arrays_by_size(obs, 42)
    if results_42:
        for path, shape, dtype in results_42:
            print(f"  Found: obs.{path} - shape={shape}, dtype={dtype}")
            print(f"    Values: {obs[path] if '.' not in path else 'nested'}")
    else:
        print("  No arrays with exactly 42 elements found!")
    
    print(f"\nSearching for arrays with >30 elements (likely joint data):")
    results_large = find_arrays_by_size(obs, None)
    results_large = [r for r in find_arrays_by_size(obs, 100, "") if any(size >= 30 for size in [x for x in range(r[1][0] if len(r[1]) == 1 else np.prod(r[1]))])]
    
    # Alternative search
    def find_large_arrays(obj, min_size=30, path=""):
        """Find arrays larger than min_size."""
        results = []
        
        if isinstance(obj, np.ndarray):
            if obj.size >= min_size:
                results.append((path, obj.shape, obj.dtype, obj.size))
        elif isinstance(obj, dict):
            for key, val in obj.items():
                results.extend(find_large_arrays(val, min_size, f"{path}.{key}" if path else key))
        elif isinstance(obj, (list, tuple)):
            for idx, item in enumerate(obj):
                results.extend(find_large_arrays(item, min_size, f"{path}[{idx}]"))
        
        return results
    
    results_large = find_large_arrays(obs, min_size=30)
    if results_large:
        for path, shape, dtype, size in results_large:
            print(f"  Found: obs.{path} - shape={shape}, dtype={dtype}, size={size}")
    else:
        print("  No arrays with >30 elements found!")

if __name__ == "__main__":
    main()
