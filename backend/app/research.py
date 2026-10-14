"""Deterministic, testable CEDAR decision and stability algorithms.

These algorithms are research prototypes. They are not credit approval, fraud
detection, or a claim that the architecture is unprecedented.
"""
from decimal import Decimal, InvalidOperation
from itertools import product
from typing import Any

OPERATORS = {"gte", "lte", "gt", "lt", "eq", "neq", "in"}
PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("Not a numeric value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Not a numeric value")
    if not result.is_finite():
        raise ValueError("Nonfinite numeric value")
    return result

def rule_status(observed: Any, operator: str, target: Any) -> str:
    """Unknown values and unsupported comparison types NEVER count as a pass."""
    if operator not in OPERATORS or observed is None:
        return UNKNOWN
    try:
        if operator == "in":
            if not isinstance(target, list):
                return UNKNOWN
            outcome = observed in target
        elif operator in ("eq", "neq"):
            outcome = observed == target
            if operator == "neq":
                outcome = not outcome
        else:
            left, right = _decimal(observed), _decimal(target)
            outcome = {
                "gte": lambda: left >= right,
                "lte": lambda: left <= right,
                "gt": lambda: left > right,
                "lt": lambda: left < right,
            }[operator]()
        return PASS if outcome else FAIL
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return UNKNOWN

def aggregate(results: list[tuple[str, bool]]) -> str:
    """Only mandatory rules determine the preliminary lender outcome."""
    mandatory = [status for status, required in results if required]
    if any(status == FAIL for status in mandatory):
        return FAIL
    if any(status == UNKNOWN for status in mandatory):
        return UNKNOWN
    return PASS

def evaluate_rules(rules: list[dict], evidence: dict[str, Any]) -> tuple[str, list[dict]]:
    details = []
    for rule in rules:
        observed = evidence.get(rule["field_key"])
        status = rule_status(observed, rule["operator"], rule["target"])
        details.append({
            "rule_id": rule["id"],
            "field_key": rule["field_key"],
            "observed": observed,
            "status": status,
            "required": rule["required"],
            "explanation": f"{rule['field_key']} {rule['operator']} {rule['target']!r}: {status}",
        })
    return aggregate([(r["status"], r["required"]) for r in details]), details

def stability(
    rules: list[dict],
    evidence: dict[str, Any],
    candidates: dict[str, list[Any]],
    limit: int = 128,
) -> dict:
    """Enumerate supported candidate worlds (including the current observation).

    Returns stable=None if the finite supported space cannot be established.
    Stability is relative to user-provided candidates; it is NOT proof of
    robustness to every possible document error.
    """
    fields = sorted({r["field_key"] for r in rules if r["required"]})
    domains = []
    count = 1
    for key in fields:
        values = [evidence[key]] if key in evidence else [None]
        for candidate in candidates.get(key, []):
            if candidate not in values:
                values.append(candidate)
        if any(isinstance(x, (dict, list)) for x in values):
            return {"stable": None, "worlds": 0, "outcomes": [], "reason": "unsupported candidate type"}
        count *= len(values)
        if count > limit:
            return {"stable": None, "worlds": count, "outcomes": [], "reason": "candidate space exceeds limit"}
        domains.append(values)
    outcomes = set()
    for values in product(*domains):
        world = dict(zip(fields, values))
        outcome, _ = evaluate_rules(rules, world)
        outcomes.add(outcome)
    return {"stable": len(outcomes) == 1, "worlds": count, "outcomes": sorted(outcomes), "reason": "supported candidate worlds"}

def affected_rule_ids(rules: list[dict], changed_evidence_keys: set[str]) -> set[int]:
    return {r["id"] for r in rules if r["field_key"] in changed_evidence_keys}

def selective_recompute(
    rules: list[dict], new_evidence: dict[str, Any],
    previous_results: list[dict], changed_keys: set[str],
) -> tuple[str, list[dict]]:
    """Reuse unaffected rule results, then check against full evaluation.

    Raises on disagreement to protect against incorrect dependency metadata.
    """
    previous = {r["rule_id"]: r for r in previous_results}
    new_status, full_details = evaluate_rules(rules, new_evidence)
    if any(r["id"] not in previous for r in rules):
        raise ValueError("Prior rule evaluation missing; full evaluation required")
    merged = []
    for new in full_details:
        if new["field_key"] in changed_keys:
            merged.append(new)
        else:
            merged.append(dict(previous[new["rule_id"]]))
    status = aggregate([(r["status"], r["required"]) for r in merged])
    if status != new_status or [(r["rule_id"], r["status"]) for r in merged] != [
        (r["rule_id"], r["status"]) for r in full_details
    ]:
        raise ValueError("Selective recompute mismatch; dependency invalidation unsafe")
    return status, merged

def review_priority(changed_lenders: int, dependent_rules: int, has_candidates: bool) -> int:
    return 10 + min(changed_lenders, 10) * 20 + min(dependent_rules, 20) * 5 + (15 if has_candidates else 0)
