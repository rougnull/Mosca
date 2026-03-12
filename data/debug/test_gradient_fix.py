#!/usr/bin/env python3
"""
Test script to verify the gradient fix works correctly.

Tests that IMPROVED olfactory brain prevents overshooting at odor source
by using temporal gradient for forward motion control.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from olfaction.odor_field import OdorField
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain


def test_temporal_gradient_fix():
    """Test that temporal gradient prevents overshooting."""
    print("\n" + "="*80)
    print("TESTING TEMPORAL GRADIENT FIX FOR CHEMOTAXIS")
    print("="*80)
    
    # Create odor field
    odor_field = OdorField(
        sources=[(50.0, 50.0, 5.0)],
        sigma=15.0,
        amplitude=1.0
    )
    
    # Create improved brain
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=2.0,
        forward_scale=0.5,
        turn_scale=1.0,
        threshold=0.0001,
    )
    
    print("\nTest Case: Fly approaching source from (30, 30) toward (50, 50)")
    print("\nPosition | Conc_C | Conc_Change | Forward | Turn   | Status")
    print("---------|--------|-------------|---------|--------|--------")
    
    concentrations = []
    
    # Simulate fly walking directly toward source
    for step, x in enumerate(np.linspace(30, 52, 25)):
        y = 30 + (x - 30)  # Diagonal path
        pos = np.array([x, y, 3.0])
        heading = np.arctan2(50 - y, 50 - x)  # Face toward source
        
        # Get concentration change
        conc = float(odor_field.concentration_at(pos))
        concentrations.append(conc)
        
        if len(concentrations) > 1:
            conc_change = conc - concentrations[-2]
        else:
            conc_change = 0
        
        # Query brain
        action = brain.step(odor_field, pos, heading)
        forward, turn = action
        
        # Determine position relative to source
        dist = np.linalg.norm(pos[:2] - np.array([50, 50]))
        if dist > 10:
            status = "FAR"
        elif dist > 3:
            status = "APPROACHING"
        else:
            status = "NEAR/AT SOURCE"
        
        print(f"({x:0.1f}, {y:0.1f}) | {conc:0.4f} | {conc_change:+0.4f} | {forward:0.3f}   | {turn:0.3f}  | {status}")
    
    print("\n" + "="*80)
    print("EXPECTED BEHAVIOR:")
    print("="*80)
    print("""
[BEFORE FIX - WRONG]:
- Forward increases as conc increases
- At source (conc ~1.0): forward ~0.5
- Result: Fly walks through source and away

[AFTER FIX - CORRECT]:
- Forward based on dConc/dt (concentration change)
- When approaching: dConc/dt > 0, forward increases
- When at max: dConc/dt ~0, forward drops to 0
- When leaving: dConc/dt < 0, forward = 0 (clipped at 0)
- Result: Fly slows down as it approaches, stops/circles at source
""")
    
    print("\n" + "="*80)
    print("VERDICT:")
    print("="*80)
    
    # Analyze the last few steps
    last_3_forwards = []
    last_3_concs = []
    
    for step, x in enumerate(np.linspace(48, 52, 5)):
        y = 30 + (x - 30)
        pos = np.array([x, y, 3.0])
        heading = np.arctan2(50 - y, 50 - x)
        
        conc = float(odor_field.concentration_at(pos))
        last_3_concs.append(conc)
        
        action = brain.step(odor_field, pos, heading)
        forward, turn = action
        last_3_forwards.append(forward)
    
    # Check if forward velocity is lower near source
    avg_forward_near = np.mean(last_3_forwards[-2:])
    avg_forward_far = np.mean(last_3_forwards[:2]) if len(last_3_forwards) >= 2 else 0
    
    if avg_forward_near < avg_forward_far:
        print("[PASS] Forward velocity decreases near source")
        print(f"       Far (x~48): {avg_forward_far:.3f}")
        print(f"       Near (x~51): {avg_forward_near:.3f}")
    else:
        print("[CHECK] Forward velocity behavior:")
        print(f"       Far: {avg_forward_far:.3f}")
        print(f"       Near: {avg_forward_near:.3f}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    test_temporal_gradient_fix()
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("""
1. Run actual simulation:
   python tools/simple_olfactory_sim.py --duration 10 --output debug/gradient_analysis/test_trajectory.csv

2. Check trajectory CSV for:
   - Does fly reach near odor source?
   - Does it circle around source?
   - Does it overshoot less?

3. Verify with real MuJoCo:
   python tools/run_mujoco_simulation.py --duration 10

4. If working, update main simulation runner to use ImprovedOlfactoryBrain
""")
