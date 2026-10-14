"""Phase 4, 6 and 7 algorithm correctness / safety regression tests."""
import pytest
from app.research import PASS, FAIL, UNKNOWN, aggregate, evaluate_rules, rule_status, stability, selective_recompute, review_priority

RULES = [
    {"id": 1, "field_key": "turnover", "operator": "gte", "target": 1500000, "required": True},
    {"id": 2, "field_key": "age", "operator": "gte", "target": 18, "required": True},
    {"id": 3, "field_key": "sector", "operator": "eq", "target": "agriculture", "required": False},
]

@pytest.mark.parametrize("observed,operator,target,want", [
    (1300000, "gte", 1500000, FAIL),
    (1800000, "gte", 1500000, PASS),
    (None, "gte", 1500000, UNKNOWN),
    ("not a number", "gte", 1500000, UNKNOWN),
    (False, "gte", 0, UNKNOWN),
    (10, "random", 1, UNKNOWN),
    ("fpo", "eq", "fpo", PASS),
    (6, "in", [3, 6, 9], PASS),
])
def test_rule_outcomes(observed, operator, target, want):
    assert rule_status(observed, operator, target) == want

def test_missing_mandatory_evidence_is_unknown():
    status, details = evaluate_rules(RULES, {"age": 30})
    assert status == UNKNOWN
    assert details[0]["status"] == UNKNOWN

def test_unstable_lender_a_stable_lender_b():
    a = stability(RULES[:1], {"turnover": 1300000}, {"turnover": [1800000]})
    b_rules = [{**RULES[0], "target": 1000000}]
    b = stability(b_rules, {"turnover": 1300000}, {"turnover": [1800000]})
    assert (a["stable"], a["outcomes"], a["worlds"]) == (False, [FAIL, PASS], 2)
    assert (b["stable"], b["outcomes"], b["worlds"]) == (True, [PASS], 2)

def test_candidate_blowup_is_unknown_not_stable():
    rules = [{"id": i, "field_key": f"x{i}", "operator": "gte", "target": 0, "required": True} for i in range(8)]
    data = {f"x{i}": 0 for i in range(8)}
    candidates = {f"x{i}": [1] for i in range(8)}
    result = stability(rules, data, candidates)
    assert result["stable"] is None and result["worlds"] == 256

def test_selective_reevaluation_exactly_equals_full():
    original = {"turnover": 1300000, "age": 25, "sector": "agriculture"}
    _, before = evaluate_rules(RULES, original)
    updated = {**original, "turnover": 1800000}
    status, results = selective_recompute(RULES, updated, before, {"turnover"})
    expected, full = evaluate_rules(RULES, updated)
    assert status == expected == PASS
    assert results == full

def test_required_fail_overrides_unknown_and_optional():
    assert aggregate([(FAIL, True), (UNKNOWN, True), (PASS, False)]) == FAIL
    assert aggregate([(UNKNOWN, True), (FAIL, False)]) == UNKNOWN

def test_impact_priority_increases():
    assert review_priority(2, 2, True) > review_priority(0, 1, False)
