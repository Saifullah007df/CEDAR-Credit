"""Typed relational schema with immutable evaluation and evidence history."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="borrower", index=True)
    lender_id: Mapped[int | None] = mapped_column(ForeignKey("lenders.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Borrower(Base):
    __tablename__ = "borrowers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    legal_name: Mapped[str] = mapped_column(String(150))
    borrower_type: Mapped[str] = mapped_column(String(32), default="fpo")

class Lender(Base):
    __tablename__ = "lenders"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class LoanProduct(Base):
    __tablename__ = "loan_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"))
    name: Mapped[str] = mapped_column(String(120))
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    max_amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    apr: Mapped[Decimal] = mapped_column(Numeric(6,3))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Application(Base):
    __tablename__ = "loan_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("borrowers.id"), index=True)
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    loan_purpose: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(150))
    mime_type: Mapped[str] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class EvidenceFact(Base):
    __tablename__ = "evidence_facts"
    __table_args__ = (UniqueConstraint("application_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    value: Mapped[object] = mapped_column(JSON)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class EvidenceRevision(Base):
    __tablename__ = "evidence_revisions"
    __table_args__ = (UniqueConstraint("fact_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey("evidence_facts.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[object] = mapped_column(JSON)
    candidates: Mapped[list] = mapped_column(JSON)
    verified: Mapped[bool] = mapped_column(Boolean)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Policy(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("lender_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PolicyRule(Base):
    __tablename__ = "policy_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policy_versions.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(100))
    operator: Mapped[str] = mapped_column(String(20))
    target: Mapped[object] = mapped_column(JSON)
    required: Mapped[bool] = mapped_column(Boolean, default=True)

class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (UniqueConstraint("policy_rule_id", "evidence_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_rule_id: Mapped[int] = mapped_column(ForeignKey("policy_rules.id"), index=True)
    evidence_key: Mapped[str] = mapped_column(String(100), index=True)

class Evaluation(Base):
    __tablename__ = "evaluation_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"), index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policy_versions.id"))
    evidence_versions: Mapped[dict] = mapped_column(JSON)
    decision: Mapped[str] = mapped_column(String(20))
    stable: Mapped[bool | None] = mapped_column(Boolean)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class RuleResult(Base):
    __tablename__ = "rule_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluation_snapshots.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("policy_rules.id"))
    status: Mapped[str] = mapped_column(String(20))
    observed: Mapped[object] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)

class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey("evidence_facts.id"), index=True)
    priority: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="open")
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class LoanOffer(Base):
    __tablename__ = "loan_offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), index=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("lenders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("loan_products.id"))
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluation_snapshots.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    apr: Mapped[Decimal] = mapped_column(Numeric(6,3))
    status: Mapped[str] = mapped_column(String(30), default="provisional")

class Loan(Base):
    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("loan_offers.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="accepted")
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Repayment(Base):
    __tablename__ = "repayments"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reference: Mapped[str] = mapped_column(String(120), default="simulated")

class UtilizationClaim(Base):
    __tablename__ = "utilization_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    category: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2))
    note: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="unverified")

class UtilizationLink(Base):
    __tablename__ = "utilization_evidence_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("utilization_claims.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    annotation: Mapped[str] = mapped_column(String(255), default="")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    object_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
