"""Phase 2 Min — two read-only checkers: change_scope and upload_package.

Public API:
  change_scope_check(task_path, frozen_dir) -> (exit_code, result_dict)
  upload_package_check(task_path, frozen_dir) -> (exit_code, result_dict)

Exit codes: 0=PASS, 1=FAIL, 2=ERROR
"""

from protocol_guard.phase2_min.change_scope_check import change_scope_check
from protocol_guard.phase2_min.upload_package_check import upload_package_check

__all__ = ["change_scope_check", "upload_package_check"]
