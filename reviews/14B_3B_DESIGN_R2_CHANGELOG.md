# 14B-3B Facing Design R2 Changelog

```text
TASK_ID: 14B_3B_DESIGN_R2C
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
```

## Revision history

| Revision | Task | Key delta |
|----------|------|-----------|
| R1 | 14B_3B_DESIGN_R1 | Initial design; incorrectly assumed all-or-nothing pre-open matching Standing |
| R2A | 14B_3B_DESIGN_R2A | Corrected configuration semantics per actual 14A schema behavior; pre-open only checks tolerance-missing case |
| R2B | 14B_3B_DESIGN_R2B | Added requirement evidence, to_3x3 semantics, matrix Strategy A confirmation, 5-operation count |
| R2B1 | 14B_3B_DESIGN_R2B1 | Added direct face+Y evidence (lines 721/1189/1388); clarified tolerance source; corrected overflow semantics; fixed source filename; deferred scope guard |
| **R2** | **14B_3B_DESIGN_R2C** | **Final**: scope guard contract design; I1/I2A/I2B/I3/E task split; I2A/I2B boundary (no NORMALIZE overlap); overflow wording fix; merged all prior revisions |

## R2 vs R2B1 delta

| Item | R2B1 | R2 |
|------|------|-----|
| Scope guard | Deferred | Full contract designed (per-function AST checks, .matrix_world + .to_3x3 counts) |
| Task split | Not defined | I1, I2A, I2B, I3, E defined with clear sub-task boundaries |
| I2A/I2B overlap | N/A | Explicitly separated: I2A=4 read/transform ops, I2B=NORMALIZE+edges |
| Overflow wording | "x*x overflow to inf then sqrt(inf)=inf or OverflowError" | Explicit: finite components pass 4a; x*x in 4b produces inf; NOT caught by 4a; caught by 4c (or 4b except) |
| to_3x3 in scope guard | Not addressed | Per-function count: both standing and facing exactly 1 to_3x3 call |
| Document structure | Two separate docs (audit + design) | Same two docs plus this changelog for traceability |
