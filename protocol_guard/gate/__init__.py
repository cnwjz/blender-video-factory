"""Phase 2A single-task execution gate MVP.

Seven stages: validate, freeze, understand, authorize, preflight, mock_execute, finalize.
Claim is an internal step of mock_execute. Evidence generation is part of finalize.

All runtime artifacts (claims, attempt states, execution results) are written to
caller-supplied runtime_root directories. Real PROJECT_STATE.yaml is never modified.
"""
