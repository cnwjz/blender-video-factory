# 14B-3B Facing Design R2C1 Changelog

```text
TASK_ID: 14B_3B_DESIGN_R2C1
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
```

## Revision history

| Revision | Task | Key delta |
|----------|------|-----------|
| R1 | 14B_3B_DESIGN_R1 | Initial design |
| R2A | 14B_3B_DESIGN_R2A | Corrected configuration semantics per 14A schema |
| R2B | 14B_3B_DESIGN_R2B | Requirement evidence, to_3x3 semantics, matrix Strategy A, 5-operation count |
| R2B1 | 14B_3B_DESIGN_R2B1 | Direct face+Y evidence (lines 721/1189/1388), tolerance source clarified, source filename corrected, scope guard deferred |
| R2C | 14B_3B_DESIGN_R2C | Scope guard contract, I1/I2A/I2B/I3/E task split, I2A/I2B boundary |
| **R2C1** | **14B_3B_DESIGN_R2C1** | **Overflow contract corrected, scope guard contradiction removed, full error order defined, I3 split into I3A+I3B** |

## R2C1 vs R2C delta

| # | Correction | Before (R2C) | After (R2C1) |
|---|-----------|-------------|--------------|
| 1 | Overflow contract | Claimed x*x necessarily produces inf from finite components, caught by 4c | `value**2` may directly raise `OverflowError` from large finite values (e.g. 1e155), caught by 4b except. The inf-via-multiplication path through 4c is a separate valid path but not the only one |
| 2 | Scope guard contradiction | Stated other functions must have 0 `.matrix_world` AND 0 `.to_3x3` (with "(not enforced)" in parentheses) | `.matrix_world`: other functions = 0 (enforced). `.to_3x3`: counted only on standing and facing (exactly 1 each); not enforced on other functions this round |
| 3 | Error collection order | Listed per-target order without full internal sequence | Full internal order: object_exists -> direct_children -> descendants -> standing -> facing. Final output still sorted lexicographically by 14A canonicalize() |
| 4 | I3 split | Single I3 task for scope guard + Blender runner + mathutils + consistency | I3A: scope guard static test update (CPython only). I3B: Blender runner, real mathutils, standing/facing independence, runner consistency protection |
