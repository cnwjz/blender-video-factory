# 14B-4A Visibility Requirement Audit R2

```text
TASK_ID: 14B_4A_VISIBILITY_DESIGN_R2
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
SUPERSEDES: 14B_4A_VISIBILITY_REQUIREMENT_AUDIT_R1.md
```

## R2 Amendment

R1 omitted runtime ERROR contracts for `hide_viewport` and `hide_render` reads. While these are simple boolean properties unlikely to fail, the locked Standing/Facing pattern requires a try/except boundary around every Blender property read. R2 fills this gap.

All other content from R1 preserved unchanged. Document conflict count remains 0. Two code-enforceable fields confirmed.
