"""Deterministic 12-month DEMO amortization; no bank payment or servicing API."""
from calendar import monthrange
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)

def month_after(at: datetime, months: int) -> datetime:
    month = (at.month - 1 + months) % 12 + 1
    year = at.year + (at.month - 1 + months) // 12
    day = min(at.day, monthrange(year, month)[1])
    return at.replace(year=year, month=month, day=day)

def demo_schedule(principal: Decimal, annual_percent: Decimal, start: datetime, months: int = 12) -> list[dict]:
    """Simple amortization with monthly compounding and final rounding adjustment.

    Simulated output only: a real lender's offer, dates, rates, fees and payment
    calculations may differ and must be reviewed independently.
    """
    if months < 1 or months > 120 or principal <= 0 or annual_percent < 0 or annual_percent > 100:
        raise ValueError("Invalid demonstration schedule inputs")
    monthly = annual_percent / Decimal(1200)
    payment = money(principal / months if monthly == 0 else principal * monthly / (1 - (1 + monthly) ** (-months)))
    balance = money(principal)
    result = []
    for i in range(1, months + 1):
        interest = money(balance * monthly)
        principal_part = money(payment - interest)
        if i == months or principal_part >= balance:
            principal_part = balance
        if principal_part < 0:
            raise ValueError("Invalid payment calculation")
        due = money(principal_part + interest)
        balance = money(balance - principal_part)
        result.append({"installment": i, "due_at": month_after(start, i),
                       "principal_due": principal_part, "interest_due": interest,
                       "amount_due": due})
    return result
