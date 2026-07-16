"""Test TECHNICAL_RESULT enum and evidence status constants."""

import pytest
from protocol_guard.result import (
    TechnicalResult,
    EvidenceStatus,
    VALID_TECHNICAL_RESULTS,
    VALID_EVIDENCE_STATUSES,
)


class TestTechnicalResult:
    def test_valid_main_results(self):
        expected = {"TECHNICAL_PASS", "TECHNICAL_FAIL", "CONSTRAINT_CONFLICT",
                    "EVIDENCE_INVALID", "SPEC_INVALID"}
        assert VALID_TECHNICAL_RESULTS == expected

    def test_evidence_recovered_not_main_result(self):
        assert "EVIDENCE_RECOVERED" not in VALID_TECHNICAL_RESULTS

    def test_technical_pass_is_valid(self):
        assert TechnicalResult("TECHNICAL_PASS") == TechnicalResult.TECHNICAL_PASS

    def test_illegal_result_rejected(self):
        with pytest.raises(ValueError):
            TechnicalResult("BOGUS_RESULT")

    def test_evidence_recovered_is_not_a_technical_result(self):
        with pytest.raises(ValueError):
            TechnicalResult("EVIDENCE_RECOVERED")


class TestEvidenceStatus:
    def test_valid_evidence_statuses(self):
        expected = {"VALID", "RECOVERED", "INVALID"}
        assert VALID_EVIDENCE_STATUSES == expected

    def test_illegal_evidence_status_rejected(self):
        with pytest.raises(ValueError):
            EvidenceStatus("BOGUS")
