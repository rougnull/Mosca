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

### What Doesn't Belong Here

❌ **User Guides/Tutorials**
- Use README.md in root instead
- Keep documentation focused on technical details

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

### For Maintenance

- **Bugs/Issues** → Document in `FIXES.md`
- **New Features** → Update `ARCHITECTURE.md` and `CHANGELOG.md`
- **Breaking Changes** → Update `CHANGELOG.md` with migration guide
- **Design Decisions** → Document in `ARCHITECTURE.md`

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
└── README.md            # This file (index)
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

- **`../README.md`** - Main project documentation (user-facing)
- **`../notebooks/`** - Jupyter notebooks for interactive exploration
- **`../debug/`** - Debug logs and temporary analysis

---

**Maintained by**: Project maintainers
**Documentation version**: 1.0.0
