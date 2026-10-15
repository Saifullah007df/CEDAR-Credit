"""Safe local bootstrapping for synthetic CEDAR-Credit test data.

Usage:
    python -m app.cli create-admin admin@example.test
    python -m app.cli seed-demo
"""
import getpass
import sys
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_engine
from app.models import Lender, LoanProduct, Policy, PolicyRule, DependencyEdge, User
from app.security import hash_password

def create_admin(email: str):
    email = email.strip().lower()
    pwd = getpass.getpass("New admin password (12+ characters): ")
    if len(pwd) < 12 or "@" not in email:
        raise SystemExit("Valid email and password of at least 12 characters required")
    with Session(get_engine()) as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists")
        user = User(email=email, password_hash=hash_password(pwd), role="platform_admin")
        db.add(user)
        db.commit()
    print("Administrator created:", email)

def seed_demo():
    """Two fictional lenders; idempotent and never overwrites existing policies."""
    lenders = (
        ("Synthetic Lender A", 1500000, "A: Demonstration Crop Loan", Decimal("11.000")),
        ("Synthetic Lender B", 1000000, "B: Demonstration FPO Loan", Decimal("12.000")),
    )
    with Session(get_engine()) as db:
        for name, turnover_floor, product_name, apr in lenders:
            lender = db.scalar(select(Lender).where(Lender.name == name))
            if not lender:
                lender = Lender(name=name)
                db.add(lender)
                db.flush()
            product = db.scalar(select(LoanProduct).where(
                LoanProduct.lender_id == lender.id, LoanProduct.name == product_name))
            if not product:
                db.add(LoanProduct(lender_id=lender.id, name=product_name,
                                   min_amount=Decimal("100000"), max_amount=Decimal("1000000"), apr=apr))
            has_policy = db.scalar(select(Policy.id).where(Policy.lender_id == lender.id))
            if not has_policy:
                policy = Policy(lender_id=lender.id, version=1, active=True)
                db.add(policy)
                db.flush()
                rule = PolicyRule(policy_id=policy.id, field_key="turnover", operator="gte",
                                  target=turnover_floor, required=True)
                db.add(rule)
                db.flush()
                db.add(DependencyEdge(policy_rule_id=rule.id, evidence_key="turnover"))
        db.commit()
    print("Synthetic lender demo seeded. No real bank or borrower records were created.")
    print("Turnover thresholds: Lender A INR 1,500,000; Lender B INR 1,000,000.")

def main():
    if len(sys.argv) == 3 and sys.argv[1] == "create-admin":
        create_admin(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "seed-demo":
        seed_demo()
    else:
        raise SystemExit("Usage: python -m app.cli create-admin EMAIL | python -m app.cli seed-demo")

if __name__ == "__main__":
    main()
