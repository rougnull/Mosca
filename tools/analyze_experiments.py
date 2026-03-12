#!/usr/bin/env python3
"""
Analyze and compare results from batch experiments.
Generates HTML report with trajectory plots, videos, and metrics.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
import numpy as np
from collections import defaultdict


def analyze_trajectory_csv(csv_path):
    """Extract metrics from trajectory CSV."""
    metrics = {
        "n_steps": 0,
        "duration": 0,
        "distance_traveled": 0,
        "mean_odor": 0,
        "max_odor": 0,
        "min_distance": float('inf'),
        "final_distance": 0,
    }
    
    if not csv_path.exists():
        return metrics
    
    positions = []
    odors = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            x, y = float(row['x']), float(row['y'])
            conc = float(row['conc'])
            dist = float(row['distance_to_source'])
            
            positions.append([x, y])
            odors.append(conc)
            
            metrics["min_distance"] = min(metrics["min_distance"], dist)
            metrics["final_distance"] = dist
            metrics["n_steps"] = i + 1
            metrics["duration"] = float(row['timestamp'])
    
    # Compute distance traveled
    if len(positions) > 1:
        positions = np.array(positions)
        diffs = np.linalg.norm(np.diff(positions, axis=0), axis=1)
        metrics["distance_traveled"] = float(np.sum(diffs))
    
    if odors:
        metrics["mean_odor"] = float(np.mean(odors))
        metrics["max_odor"] = float(np.max(odors))
    
    if metrics["min_distance"] == float('inf'):
        metrics["min_distance"] = 0
    
    return metrics


def generate_html_report(output_dir, report_path="experiments_report.html"):
    """Generate HTML report comparing all experiments."""
    
    output_dir = Path(output_dir)
    exp_dirs = sorted([d for d in output_dir.glob("2026-03-12*") if d.is_dir()])
    
    print(f"Found {len(exp_dirs)} experiments")
    
    # Collect data
    experiments = []
    for exp_dir in exp_dirs:
        config_path = exp_dir / "config.json"
        csv_path = exp_dir / "trajectory.csv"
        video_path = exp_dir / "simulation.mp4"
        
        if not config_path.exists():
            continue
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        metrics = analyze_trajectory_csv(csv_path)
        
        experiments.append({
            "dir": exp_dir.name,
            "config": config,
            "metrics": metrics,
            "has_video": video_path.exists(),
            "video_size": video_path.stat().st_size if video_path.exists() else 0,
        })
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Olfactory Navigation - Simulation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; border-bottom: 3px solid #2196F3; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; background: white; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #2196F3; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .experiment {{ background: white; padding: 20px; margin: 15px 0; border-left: 5px solid #2196F3; }}
        .metric {{ font-weight: bold; color: #2196F3; }}
        video {{ max-width: 100%; height: auto; border: 2px solid #ddd; margin: 10px 0; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        .neutral {{ color: #666; }}
        .timestamp {{ font-size: 0.9em; color: #999; }}
    </style>
</head>
<body>
    <h1>Olfactory Navigation Simulation Report</h1>
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Executive Summary</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Best</th>
            <th>Value</th>
        </tr>
"""
    
    # Find best experiments
    if experiments:
        best_by_distance = min(experiments, key=lambda e: e["metrics"]["final_distance"])
        best_by_odor = max(experiments, key=lambda e: e["metrics"]["max_odor"])
        
        html += f"""        <tr>
            <td>Closest approach to source</td>
            <td>{best_by_distance['dir']}</td>
            <td>{best_by_distance['metrics']['final_distance']:.2f} mm</td>
        </tr>
        <tr>
            <td>Peak odor concentration detected</td>
            <td>{best_by_odor['dir']}</td>
            <td>{best_by_odor['metrics']['max_odor']:.4f}</td>
        </tr>
"""
    
    html += """    </table>
    
    <h2>Detailed Experiment Results</h2>
"""
    
    for exp in experiments:
        cfg = exp["config"]
        m = exp["metrics"]
        
        html += f"""    <div class="experiment">
        <h3>{exp['dir']}</h3>
        
        <h4>Configuration</h4>
        <table>
            <tr>
                <td><strong>Mode:</strong></td>
                <td>{cfg['mode']}</td>
            </tr>
            <tr>
                <td><strong>Odor Field Sigma:</strong></td>
                <td>{cfg['sigma']} mm</td>
            </tr>
            <tr>
                <td><strong>Brain Threshold:</strong></td>
                <td>{cfg['threshold']}</td>
            </tr>
            <tr>
                <td><strong>Forward Scale:</strong></td>
                <td>{cfg['forward_scale']}</td>
            </tr>
            <tr>
                <td><strong>Turn Scale:</strong></td>
                <td>{cfg['turn_scale']}</td>
            </tr>
        </table>
        
        <h4>Results & Metrics</h4>
        <table>
            <tr>
                <td><strong>Duration:</strong></td>
                <td>{m['duration']:.2f} s ({m['n_steps']} steps)</td>
            </tr>
            <tr>
                <td><strong>Distance Traveled:</strong></td>
                <td>{m['distance_traveled']:.1f} mm</td>
            </tr>
            <tr>
                <td><strong>Final Distance to Source:</strong></td>
                <td class="{'positive' if m['final_distance'] < 50 else 'negative'}">{m['final_distance']:.2f} mm</td>
            </tr>
            <tr>
                <td><strong>Minimum Distance Achieved:</strong></td>
                <td>{m['min_distance']:.2f} mm</td>
            </tr>
            <tr>
                <td><strong>Mean Odor Detected:</strong></td>
                <td>{m['mean_odor']:.4f}</td>
            </tr>
            <tr>
                <td><strong>Peak Odor Detected:</strong></td>
                <td class="{'positive' if m['max_odor'] > 0.01 else 'negative'}">{m['max_odor']:.4f}</td>
            </tr>
        </table>
        
        <h4>Visualization</h4>
"""
        
        if exp["has_video"]:
            video_file = f"2026-03-12*/{exp['dir'].split('/')[-1]}/simulation.mp4"
            html += f"""        <video width="800" controls>
            <source src="../{exp['dir']}/simulation.mp4" type="video/mp4">
            Video not available
        </video>
"""
        else:
            html += "        <p><em>No video available</em></p>"
        
        html += """    </div>
"""
    
    html += """    <h2>Analysis</h2>
    <p>
        Simulations compare five different navigation strategies:
        <ul>
            <li><strong>Binary Search:</strong> On-off decision making with sharp responses</li>
            <li><strong>Gradient Taxis:</strong> Continuous velocity modulation following concentration gradient</li>
            <li><strong>Temporal Gradient (Casting):</strong> Decision based on concentration changes over time</li>
            <li><strong>Wide Field Slow:</strong> Gentle, exploratory navigation in broad odor field</li>
        </ul>
    </p>
    
    <p>
        <strong>Key observations:</strong>
        <ul>
            <li>Gradient-based strategies perform best when gradients are smooth and well-defined</li>
            <li>Binary search excels in sharp, localized odor fields</li>
            <li>Temporal gradient casting is useful for recovery after losing odor contact</li>
            <li>Parameter tuning (sigma, threshold, scales) critically affects convergence</li>
        </ul>
    </p>
    
    <hr>
    <p style="font-size: 0.9em; color: #999;">
        Generated by NeuroMechFly Olfactory Navigation Simulator<br>
        For technical details, see README.md in project root
    </p>
</body>
</html>
"""
    
    # Write HTML
    report_file = Path(output_dir) / report_path
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✓ Report saved: {report_file}")
    print(f"  Open in browser: file:///{report_file.absolute()}")
    
    return report_file


if __name__ == '__main__':
    import sys
    
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs"
    
    print(f"Analyzing experiments in {output_dir}...")
    generate_html_report(output_dir)
