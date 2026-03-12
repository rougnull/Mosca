# Technical Documentation

**Last Updated**: 2026-03-12

This directory contains technical documentation for the Mosca project.

---

## Core Documentation

### 📐 [ARCHITECTURE.md](ARCHITECTURE.md)
**System Architecture and Design**

Complete technical overview of the system:
- High-level pipeline and abstraction levels
- Core components (OdorField, ImprovedOlfactoryBrain, BrainFly, CPG)
- Directory structure
- Key design decisions
- Performance considerations
- Biological validation
- Extension points

**Audience**: Developers, researchers understanding the system

---

### 🔧 [FIXES.md](FIXES.md)
**Bug Fixes and Solutions**

All issues resolved in the project:
- Import dependency handling (tqdm, numpy, FlyGym)
- BrainFly architecture corrections
- Camera API and optional rendering
- Best practices and patterns
- Testing checklist

**Audience**: Developers troubleshooting issues

---

### 📋 [CHANGELOG.md](CHANGELOG.md)
**Version History**

Complete change history:
- Version 1.0.0 features and fixes
- Development history
- Migration guides
- Commit categorization

**Audience**: Maintainers, developers tracking changes

---

## Project Standards and Development Rules

### 1. File and Folder Management

#### 1.1 Directory Structure

**`/tools`** - Executable Scripts
- Only FUNCTIONAL scripts with a SINGLE, CLEAR responsibility
- 1 main entry point per module (e.g., `simulate_chemotaxis.py`)
- Debug scripts go to `/tools/debug/` (NOT in root of tools)
- NO thematic folders (e.g., "3d_simulations", "analysis_tools")
- Maximum 1 file per functionality; use CLI parameters for variants

**`/outputs/simulations`** - ONLY folder for simulation results
- Structure: `/outputs/simulations/{SIMULATION_TYPE}/{TIMESTAMP}/`
- Valid types: `chemotaxis_3d/`, `olfactory_2d/`, `behavioral_test/`, `physics_3d/`
- NO arbitrary subdirectories (e.g., `3d_simulations/` is FORBIDDEN)
- Include metadata in JSON/YAML with each simulation

**`/outputs/debug`** - ONLY folder for logs and diagnostic data
- Only files generated during debugging/testing
- Use timestamps in names: `debug_2026-03-12_14-32.log`

**`/data/docs`** - Technical Documentation ONLY
- Only `.md` files describing implementations and architectural changes
- FORBIDDEN: user guides, tutorials, "session changes", examples
- Keep updated list of modules in `CHANGELOG.md`

#### 1.2 Redundancy Management

**FORBIDDEN**: Create multiple scripts with the same purpose

**REQUIRED**: Combine into 1 main file with CLI options

**Example CORRECT:**
```python
# tools/validate_simulation.py (SINGLE file with all tests)
if args.test == "angles":          # ENABLE
    test_angle_ranges()
elif args.test == "flygym":        # ENABLE
    test_flygym_integration()
elif args.test == "all":           # RUN ALL
    run_all_tests()
```

**Example INCORRECT:**
```
tools/test_angles.py               # ❌ FORBIDDEN
tools/test_flygym.py               # ❌ FORBIDDEN
tools/test_behavior.py             # ❌ FORBIDDEN
```

### 2. Script Naming and Categorization

#### 2.1 Naming Convention in /tools:

```
simulate_*.py         - Simulation scripts (main execution)
process_*.py          - Data transformation/postprocessing
analyze_*.py          - Results analysis
validate_*.py         - Testing and verification
render_*.py           - Visualization generation
debug_*.py            - Diagnostic tools (e.g., debug_angles.py)
```

#### 2.2 Single Entry Point

- For each major functionality, 1 main script in `/tools`
- Variants controlled with CLI arguments (`--option value`)
- DO NOT copy/modify scripts without changing the name (e.g., `render_final.py`, `render_simple.py` → INCORRECT)

### 3. Version Control and Outputs

#### 3.1 Simulation Outputs

**Required path**: `/outputs/simulations/{TYPE}/{TIMESTAMP}/`

**Files ALWAYS included:**
- `metadata.json` - Parameters, code version, timestamp
- `simulation_data.pkl` - Raw simulation data
- `video.mp4` - Visualization (if applicable)
- `summary.txt` - Execution summary

#### 3.2 Git Ignore

- In `.gitignore` DO NOT include `/outputs` or `/data/debug`
- All results should be shared in repository
- Be selective: exclude only temporary files (`.tmp`, `*.swp`)

### 4. Documentation and Code Changes

#### 4.1 Documenting Changes

- EVERY architecture change → update `/data/docs/CHANGELOG.md`
- EVERY new script → describe in `/data/docs/CHANGELOG.md`
- Required format:
  ```markdown
  ## Change: [Module Name]
  - **File**: path/file.py
  - **Change**: [Technical description]
  - **Reason**: [Why it was necessary]
  - **Impact**: [What other modules it affects]
  ```

#### 4.2 Forbidden

- ❌ `.md` files with "user guides" or "tutorials"
- ❌ `.md` files documenting "developer session changes"
- ❌ Code comments explaining "what AI did in session X"
- ✅ Document TECHNICAL RESULTS and ARCHITECTURAL DECISIONS only

### 5. Pre/Post Execution Validation

#### 5.1 Pre-execution (REQUIRED)

- [ ] Verify output path (always `/outputs/simulations/...`)
- [ ] Verify no new thematic folders
- [ ] Verify no redundant scripts in `/tools`
- [ ] Verify metadata + logging in the script
- [ ] Execute with `--dry-run` or verbose to validate behavior

#### 5.2 Post-execution (REQUIRED)

- [ ] Inspect generated outputs (metadata.json, video.mp4, etc)
- [ ] Verify video duration (> 0.5 seconds for movement video)
- [ ] Verify data (shape, values, no NaN)
- [ ] Document in `/data/docs/CHANGELOG.md` if there are changes

### 6. Known Issues and Bug Tracking

See **[FIXES.md](FIXES.md)** for resolved issues.

**Current Known Issues:**

#### 6.1 FlyGym Rendering (RESOLVED - 2026-03-12)
- **Issue**: `SingleFlySimulation.render()` only returned valid frame at step 0, then returned [None]
- **Status**: ✅ RESOLVED - Rendering now optional (default: disabled)
- **Solution**: Separated physics from rendering, fixed Camera API
- **See**: FIXES.md Issue #4

#### 6.2 MuJoCo Physical Instability (RESOLVED - 2026-03-12)
- **Issue**: Applying dynamic angles from pickle caused NaN/Inf in first steps
- **Status**: ✅ RESOLVED - Physics-based simulation from start
- **Solution**: Use FlyGym physics with CPG controller instead of kinematic approach
- **See**: CHANGELOG.md v1.0.0

---

## Documentation Organization

### What Belongs Here

✅ **Technical Architecture**
- System design decisions
- Component interactions
- Implementation details
- Performance characteristics

✅ **Bug Fixes and Solutions**
- Root cause analysis
- Solutions implemented
- Code patterns established
- Testing strategies

✅ **Change History**
- Version releases
- Feature additions
- Breaking changes
- Migration guides

✅ **Project Standards**
- File organization rules
- Naming conventions
- Development workflow
- Quality standards

### What Doesn't Belong Here

❌ **User Guides/Tutorials**
- How-to guides for end users
- Step-by-step tutorials
- Usage examples (these go in main README.md if needed)

❌ **Session Notes**
- Temporary analysis files
- Debug session logs
- Work in progress notes

❌ **Redundant Information**
- Duplicate fix descriptions
- Overlapping architecture docs
- Multiple versions of same content

---

## Quick Reference

### For New Developers

1. **Start with** `../README.md` - Project overview and quick start
2. **Then read** `ARCHITECTURE.md` - Understand system design
3. **Reference** `FIXES.md` - Common issues and solutions
4. **Track changes** `CHANGELOG.md` - Recent updates
5. **Follow standards** - This document (project rules)

### For Maintenance

- **Bugs/Issues** → Document in `FIXES.md`
- **New Features** → Update `ARCHITECTURE.md` and `CHANGELOG.md`
- **Breaking Changes** → Update `CHANGELOG.md` with migration guide
- **Design Decisions** → Document in `ARCHITECTURE.md`
- **New Scripts** → Follow naming conventions, document in `CHANGELOG.md`

### For Research

- **Biological Parameters** → See `ARCHITECTURE.md` section "Biological Validation"
- **References** → See `../README.md` section "References"
- **Validation Data** → See `ARCHITECTURE.md` section "Parameters Validated"

---

## Documentation Standards

### File Organization

```
data/docs/
├── ARCHITECTURE.md       # System design (technical)
├── FIXES.md             # Bug fixes and solutions
├── CHANGELOG.md         # Version history
└── README.md            # This file (index + standards)
```

### Writing Style

- **Concise**: Focus on facts and technical details
- **Structured**: Use clear hierarchies and sections
- **Code-first**: Show code examples, not just descriptions
- **Cross-referenced**: Link between related documents

### Maintenance

- **Update on change**: Keep docs synchronized with code
- **Remove obsolete**: Delete outdated information
- **Consolidate**: Merge related documents
- **Version**: Date all major updates

---

## Historical Documentation (Archived)

The following files were consolidated into the current structure:

**Merged into FIXES.md:**
- `COMPLETE_FIX_SUMMARY.md`
- `FIX_CAMERA_OPTIONAL_RENDERING.md`
- `FIX_BRAINFLY_ARCHITECTURE.md`
- `FIX_TQDM_OPTIONAL.md`
- `IMPORT_ERRORS_FIXED.md`

**Merged into ARCHITECTURE.md:**
- `ARCHITECTURE_ANALYSIS.md`
- `PHYSICS_SIMULATION_IMPLEMENTATION.md`
- `RENDERING_ARCHITECTURE.md`

**Merged into CHANGELOG.md:**
- `SUMMARY_OF_CHANGES.md`
- `IMPLEMENTATION_SUMMARY.md`
- `IMPLEMENTATION_3D_FIXES.md`

**Removed (redundant or user-facing):**
- `WORKFLOW_GUIDE.md` (user guide content moved to main README)
- `EXECUTIVE_SUMMARY.md` (high-level content in main README)
- `COMPLETE_CODE_REVIEW.md` (analysis findings integrated)
- `DIAGNOSTIC_SUMMARY.md` (fixes documented in FIXES.md)
- `DIAGNOSTIC_SIMULATION_ISSUES.md` (fixes documented in FIXES.md)
- `SUMMARY_ANALYSIS.md` (content integrated)

---

## Related Files

- **`../README.md`** - Main project documentation
- **`../notebooks/`** - Jupyter notebooks for interactive exploration
- **`../debug/`** - Debug logs and temporary analysis

---

**Maintained by**: Project maintainers
**Documentation version**: 1.0.0
