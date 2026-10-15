from app.document_extraction import heuristic_candidates
from app.research import rule_status

def test_context_numeric_extraction_is_unverified():
    suggestions = heuristic_candidates("Annual turnover: INR 13,00,000.00 and gross sales Rs 18,00,000")
    assert suggestions["turnover"] == [1300000, 1800000]

def test_unrelated_numeric_sequences_not_credit_evidence():
    assert heuristic_candidates("invoice 12345 payable 4000") == {}

def test_unverified_extraction_does_not_override_rules():
    assert rule_status(1300000, "gte", 1500000) == "FAIL"
