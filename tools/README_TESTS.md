# Test Suite Documentation

## Running Tests

To run all component tests sequentially:

```bash
python tools/test_all_components.py
```

This consolidated test suite runs three levels of testing:

### Test 1: Brain Isolated Test
- **Purpose**: Verify brain algorithm works correctly without physics
- **Steps**: 15 steps with curved trajectory
- **Expected**: Non-zero turn signals (typically -0.8 to -0.09)
- **Duration**: < 1 second

### Test 2: Observation Extraction Test
- **Purpose**: Verify BrainFly correctly extracts position and heading from FlyGym observations
- **Steps**: Tests 10 different observations
- **Expected**: All extractions successful, non-zero turn signals
- **Duration**: < 1 second

### Test 3: Short Physics Simulation
- **Purpose**: Verify full integration with FlyGym physics
- **Steps**: 200 physics steps (0.02 seconds simulated time)
- **Expected**: Non-zero turn signals, fly moves ~0.7mm with heading change
- **Duration**: ~30-60 seconds
- **Note**: Requires FlyGym installed (`pip install flygym`)

## Individual Test Files

The original individual test files are still available:

- `test_brain_isolated.py` - Brain only (no physics)
- `test_observation_extraction.py` - Observation extraction only
- `test_short_simulation.py` - Physics simulation only

## Test Results Interpretation

### Success Indicators
- ✅ Turn signals are non-zero (typically -0.8 to -0.05)
- ✅ Forward signals respond to concentration gradients
- ✅ Fly moves and changes heading during physics simulation
- ✅ No ground penetration (Z > 0)

### Failure Indicators
- ❌ Turn signals essentially zero (< 1e-6)
- ❌ Extraction returns None or [0,0,0]
- ❌ Fly doesn't move in physics simulation
- ⚠️ Ground penetration (Z < 0)

## Known Issues Fixed

1. **TypeError in observation extraction test**: Fixed handling of None return values when extraction fails with incorrect observation structure

2. **Numpy array observation structure**: Fixed BrainFly to handle `obs["fly"]` as np.ndarray (not just tuple/list). FlyGym can return observations in any of these formats.

3. **Extended simulation steps**: Increased from 50 to 200 steps to make fly movement more noticeable in physics test

## Debugging Tips

If tests fail:

1. Check that all dependencies are installed:
   ```bash
   pip install numpy flygym
   ```

2. Look for debug output in the first 5 steps - it shows:
   - Observation structure type
   - Extracted position and heading
   - Brain output (forward, turn)

3. Common issues:
   - If position extracts as [0,0,0]: observation structure mismatch
   - If heading extracts as 0.0: orientation data not in expected format
   - If turn signal is zero: check that ImprovedOlfactoryBrain is being used

4. Run individual tests to isolate the issue:
   ```bash
   python tools/test_brain_isolated.py        # Test brain only
   python tools/test_observation_extraction.py # Test extraction only
   python tools/test_short_simulation.py       # Test physics only
   ```
