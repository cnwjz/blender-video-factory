"""TECHNICAL_RESULT enum and evidence status constants.

Spec: only these 5 main results exist. EVIDENCE_RECOVERED is NOT a main result.
"""

from enum import Enum


class TechnicalResult(Enum):
    TECHNICAL_PASS = "TECHNICAL_PASS"
    TECHNICAL_FAIL = "TECHNICAL_FAIL"
    CONSTRAINT_CONFLICT = "CONSTRAINT_CONFLICT"
    EVIDENCE_INVALID = "EVIDENCE_INVALID"
    SPEC_INVALID = "SPEC_INVALID"


class EvidenceStatus(Enum):
    VALID = "VALID"
    RECOVERED = "RECOVERED"
    INVALID = "INVALID"


VALID_TECHNICAL_RESULTS = frozenset(r.value for r in TechnicalResult)
VALID_EVIDENCE_STATUSES = frozenset(s.value for s in EvidenceStatus)
