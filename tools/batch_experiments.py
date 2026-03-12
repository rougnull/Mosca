#!/usr/bin/env python3
"""
Run batch of olfactory navigation simulations with different parameters.
Creates organized outputs with date-time stamped directories.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime


EXPERIMENTS = [
    {
        "name": "Binary_Search_Sharp",
        "mode": "binary",
        "sigma": 5.0,
        "threshold": 0.1,
        "forward_scale": 1.0,
        "turn_scale": 1.5,
        "duration": 10,
    },
    {
        "name": "Gradient_Taxis_Medium",
        "mode": "gradient",
        "sigma": 15.0,
        "threshold": 0.1,
        "forward_scale": 1.0,
        "turn_scale": 1.0,
        "duration": 10,
    },
    {
        "name": "Gradient_Taxis_Aggressive",
        "mode": "gradient",
        "sigma": 15.0,
        "threshold": 0.05,
        "forward_scale": 1.5,
        "turn_scale": 1.5,
        "duration": 10,
    },
    {
        "name": "Temporal_Gradient_Casting",
        "mode": "temporal_gradient",
        "sigma": 2.0,
        "threshold": 0.05,
        "forward_scale": 0.8,
        "turn_scale": 1.5,
        "duration": 10,
    },
    {
        "name": "Wide_Field_Slow",
        "mode": "gradient",
        "sigma": 30.0,
        "threshold": 0.2,
        "forward_scale": 0.5,
        "turn_scale": 0.5,
        "duration": 10,
    },
]


def run_experiment(exp_dict, python_exe, output_dir):
    """Run single experiment."""
    cmd = [
        python_exe,
        "tools/run_simulation.py",
        "--mode", exp_dict["mode"],
        "--sigma", str(exp_dict["sigma"]),
        "--threshold", str(exp_dict["threshold"]),
        "--forward-scale", str(exp_dict["forward_scale"]),
        "--turn-scale", str(exp_dict["turn_scale"]),
        "--duration", str(exp_dict["duration"]),
        "--output-dir", output_dir,
        "--fps", "20",
    ]
    
    print(f"\n{'='*70}")
    print(f"EXPERIMENT: {exp_dict['name']}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, cwd=str(Path(__file__).parent.parent))
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Run batch of olfactory navigation experiments"
    )
    parser.add_argument('--experiments', type=str, nargs='+', default=None,
                       help='Run only specific experiments (by name)')
    parser.add_argument('--output-dir', type=str, default='outputs',
                       help='Base output directory')
    parser.add_argument('--python', type=str, default=None,
                       help='Python executable (auto-detect if not provided)')
    
    args = parser.parse_args()
    
    # Determine python executable
    if args.python is None:
        # Try to auto-detect virtual environment
        venv_dir = Path(".venv")
        if venv_dir.exists():
            python_exe = str(venv_dir / "Scripts" / "python.exe")
        else:
            python_exe = "python"
    else:
        python_exe = args.python
    
    # Filter experiments
    if args.experiments:
        experiments = [e for e in EXPERIMENTS if e["name"] in args.experiments]
        if not experiments:
            print(f"ERROR: No experiments found with names: {args.experiments}")
            return 1
    else:
        experiments = EXPERIMENTS
    
    # Run experiments
    print(f"\n{'#'*70}")
    print(f"# BATCH OLFACTORY NAVIGATION EXPERIMENTS")
    print(f"# Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    print(f"Running {len(experiments)} experiments...")
    print(f"Output directory: {args.output_dir}")
    print(f"Python: {python_exe}")
    
    results = {}
    for exp in experiments:
        success = run_experiment(exp, python_exe, args.output_dir)
        results[exp["name"]] = "✓" if success else "✗"
    
    # Summary
    print(f"\n{'='*70}")
    print(f"EXPERIMENT RESULTS")
    print(f"{'='*70}")
    for name, status in results.items():
        print(f"{status} {name}")
    
    n_success = sum(1 for s in results.values() if s == "✓")
    print(f"\n{n_success}/{len(results)} experiments completed successfully")
    
    return 0 if n_success == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
