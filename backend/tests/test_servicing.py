from datetime import datetime, timezone
from decimal import Decimal
from app.servicing import demo_schedule

def test_amortization_conserves_principal_and_dates():
    base = datetime(2026, 1, 31, tzinfo=timezone.utc)
    rows = demo_schedule(Decimal("500000"), Decimal("11"), base)
    assert len(rows) == 12
    assert rows[0]["due_at"].month == 2 and rows[0]["due_at"].day == 28
    assert sum((x["principal_due"] for x in rows), Decimal(0)) == Decimal("500000.00")
    assert all(r["amount_due"] > 0 for r in rows)

def test_zero_percent_repayment():
    rows = demo_schedule(Decimal("1200"), Decimal(0), datetime.now(timezone.utc))
    assert all(x["interest_due"] == 0 for x in rows)
    assert sum((x["amount_due"] for x in rows), Decimal(0)) == Decimal("1200.00")
