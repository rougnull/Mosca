#!/usr/bin/env python3
"""
Debug script to analyze why fly moves away when close to odor source.

Tests hypothesis: gradient logic is correct but forward behavior is wrong.
When fly is at the source:
- conc_left ≈ conc_right (gradient ≈ 0, turn ≈ 0) ✓
- But forward is maximum because conc is maximum
- This causes fly to walk straight through and away

Solution: Forward should be modulated by gradient magnitude or temporal change.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from olfaction.odor_field import OdorField
from controllers.olfactory_brain import OlfactoryBrain
from controllers.improved_olfactory_brain import ImprovedOlfactoryBrain


def test_basic_brain():
    """Test basic OlfactoryBrain in gradient mode."""
    print("\n" + "="*70)
    print("TEST 1: Basic OlfactoryBrain (Gradient Mode)")
    print("="*70)
    
    brain = OlfactoryBrain(mode="gradient", threshold=0.01, forward_scale=1.0, turn_scale=1.0)
    
    # Simulate concentrations from far to near source
    test_concs = [0.0, 0.01, 0.05, 0.1, 0.3, 0.5, 0.8, 0.95, 1.0]
    
    print("\nConc  | Forward | Turn | Status")
    print("------|---------|------|--------")
    for conc in test_concs:
        action = brain.step(conc)
        forward, turn = action[0], action[1]
        
        # How close to source?
        if conc < 0.1:
            status = "Far"
        elif conc < 0.5:
            status = "Medium"
        else:
            status = "Near/At source"
        
        print(f"{conc:0.2f}  | {forward:0.3f}   | {turn:0.3f}  | {status}")
    
    print("\n[ISSUE] Forward increases with concentration.")
    print("        At source (conc=1.0): forward=1.0, which makes fly walk away!")


def test_improved_brain_bilateral():
    """Test ImprovedOlfactoryBrain with bilateral sensing."""
    print("\n" + "="*70)
    print("TEST 2: ImprovedOlfactoryBrain (Bilateral Gradient)")
    print("="*70)
    
    # Create odor field
    odor_field = OdorField(
        sources=[(50.0, 50.0, 5.0)],
        sigma=15.0,
        amplitude=1.0
    )
    
    brain = ImprovedOlfactoryBrain(
        bilateral_distance=2.0,
        forward_scale=0.5,
        turn_scale=1.0,
        threshold=0.0001
    )
    
    # Simulate fly approaching source along straight line
    print("\nSimulating fly approaching source from (30, 30) to (50, 50)...")
    print("\nX    | Y    | Conc_C | Conc_L | Conc_R | Grad  | Forward | Turn   | Dist_to_source")
    print("------|------|--------|--------|--------|-------|---------|--------|----------------")
    
    for x in np.linspace(30, 51, 22):
        y = 30 + (x - 30) * (50 - 30) / (50 - 30)  # Move along diagonal
        pos = np.array([x, y, 3.0])
        heading = np.arctan2(50 - y, 50 - x)
        
        action = brain.step(odor_field, pos, heading)
        forward, turn = action[0], action[1]
        
        # Get individual concentrations for analysis
        conc_center = float(odor_field.concentration_at(pos))
        
        left_angle = heading + np.pi / 2
        left_pos = pos + 2.0 * np.array([np.cos(left_angle), np.sin(left_angle), 0])
        conc_left = float(odor_field.concentration_at(left_pos))
        
        right_angle = heading - np.pi / 2
        right_pos = pos + 2.0 * np.array([np.cos(right_angle), np.sin(right_angle), 0])
        conc_right = float(odor_field.concentration_at(right_pos))
        
        grad = conc_left - conc_right
        dist = np.linalg.norm(pos[:2] - np.array([50, 50]))
        
        print(f"{x:0.1f} | {y:0.1f} | {conc_center:0.4f} | {conc_left:0.4f} | {conc_right:0.4f} | {grad:0.3f} | {forward:0.3f}   | {turn:0.3f}   | {dist:0.2f}")
    
    print("\n[ISSUE] When very close to source:")
    print("        - Conc_L ~= Conc_R (gradient ~= 0) [OK] Correct")
    print("        - Turn ~= 0")
    print("        - But Forward ~= 0.5 (based on center conc)")
    print("        - SO: Fly walks straight ahead with no turning!")
    print("        - Result: Overshooting and moving away")


def analyze_problem():
    """Explain the fundamental problem."""
    print("\n" + "="*70)
    print("ROOT CAUSE ANALYSIS")
    print("="*70)
    
    print("""
The problem is in how forward velocity is calculated:

CURRENT LOGIC (WRONG):
  forward = forward_scale * concentration_at_center

ISSUE:
  When fly is AT the source:
  - concentration → 1.0 (maximum)
  - forward → maximum
  - gradient → 0 (no turning signal)  
  - Result: Fly walks straight through the source at full speed and away!

SOLUTION OPTIONS:

1. TEMPORAL GRADIENT (Best for chemotaxis):
   forward ∝ d(concentration)/dt
   - Only move forward if concentration is INCREASING
   - Stop or reverse if concentration is DECREASING
   - Natural behavior: fly overshoots once, then turns back
   
2. SPATIAL-TEMPORAL COMBINATION:
   forward ∝ gradient_magnitude
   - Move forward proportional to how "steep" the gradient is
   - At source gradient=0, so forward=0
   - Fly will circle at source without overshooting
   
3. DISTANCE-BASED MODULATION:
   forward ∝ distance_to_previous_position
   - Harder to implement, less biologically plausible

4. GRADIENT MAGNITUDE:
   Let M = |gradient_left_right|
   forward = forward_scale * concentration * (1 - exp(-M/threshold))
   - When gradient is large (far from source): forward is full
   - When gradient is small (near source): forward is reduced
   - Creates smooth deceleration as fly approaches center
   
RECOMMENDED: Option 1 (Temporal Gradient)
- Most similar to how real flies navigate
- Simplest to implement
- Most effective behavior
""")


def suggest_fix():
    """Suggest code fixes."""
    print("\n" + "="*70)
    print("SUGGESTED CODE FIX")
    print("="*70)
    
    print("""
FILE: src/controllers/improved_olfactory_brain.py
METHOD: step()

CURRENT (Lines ~110-125):
    forward = self.forward_scale * np.clip(conc_center, 0, 1)
    turn = self.turn_scale * np.clip(gradient_difference, -1, 1)

PROPOSED FIX (Temporal Gradient):
    # Calculate temporal change in concentration
    if len(self._concentration_history) >= 2:
        conc_change = conc_center - self._concentration_history[-1]
    else:
        conc_change = 0
    
    # Forward only when concentration is INCREASING
    forward = self.forward_scale * np.clip(conc_change * 10, 0, 1)
    
    # Turn based on bilateral gradient (unchanged)
    turn = self.turn_scale * np.clip(gradient_difference, -1, 1)
    
    # Store for next step
    self._concentration_history.append(conc_center)
    if len(self._concentration_history) > 10:
        self._concentration_history.pop(0)

ALTERNATIVE (Gradient Magnitude):
    # Forward proportional to gradient steepness
    gradient_magnitude = np.abs(gradient_difference)
    forward = (self.forward_scale * conc_center * 
               np.exp(-gradient_magnitude / 0.1))
    
    turn = self.turn_scale * gradient_difference


FILES TO MODIFY:
1. src/controllers/improved_olfactory_brain.py
2. Add debug logging in: tools/debug_gradient_issue.py
3. Update: tools/simple_olfactory_sim.py (to use ImprovedOlfactoryBrain)
4. Add diagnostics to: tools/generate_analysis_report.py

DEBUG DATA TO COLLECT:
- Concentration at fly position over time
- Temporal derivative (change in conc)
- Gradient magnitude
- Forward/turn commands over time
- Distance to source over time
- Fly behavior classification (approaching/at_source/leaving)
""")


if __name__ == "__main__":
    test_basic_brain()
    test_improved_brain_bilateral()
    analyze_problem()
    suggest_fix()
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("""
1. Modify ImprovedOlfactoryBrain to use temporal gradient for forward
2. Update SimpleOlfactorySim to use ImprovedOlfactoryBrain
3. Run test simulation and collect debug_gradient_analysis/
4. Verify fly now circles at source instead of overshooting
5. Investigate MuJoCo video generation issue
6. Integrate with actual FlyGym physics when working
""")
