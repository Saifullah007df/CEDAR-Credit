"""Protected marketplace and CEDAR research API, synthetic/mock prototype only.

Invariant: these endpoints report *preliminary* eligibility, never lender approval.
"""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db import get_db
from app.models import (
    Application, Borrower, DependencyEdge, Document, EvidenceFact, EvidenceRevision,
    Evaluation, Lender, Loan, LoanOffer, LoanProduct, Policy, PolicyRule, Repayment,
    ReviewTask, RuleResult, User, UtilizationClaim, UtilizationLink,
)
from app.research import (
    PASS, UNKNOWN, evaluate_rules, review_priority, selective_recompute, stability,
)
from app.security import audit, current_user, hash_password, roles

router = APIRouter(prefix="/api/v1", tags=["marketplace"])

class LenderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

class LenderUserCreate(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=128)

class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    min_amount: Decimal = Field(gt=0)
    max_amount: Decimal = Field(gt=0)
    apr: Decimal = Field(ge=0, le=100)

class ApplicationCreate(BaseModel):
    requested_amount: Decimal = Field(gt=0, le=100000000)
    loan_purpose: str = Field(min_length=2, max_length=150)

class EvidenceCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,99}$")
    value: Any = None
    candidates: list[Any] = Field(default_factory=list, max_length=30)
    document_id: int | None = None

class RuleCreate(BaseModel):
    field_key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,99}$")
    operator: str = Field(pattern="^(gte|lte|gt|lt|eq|neq|in)$")
    target: Any
    required: bool = True

class PolicyCreate(BaseModel):
    rules: list[RuleCreate] = Field(min_length=1, max_length=30)

class EvidenceVerify(BaseModel):
    value: Any
    note: str = Field(default="Manually verified from source", max_length=255)

class OfferCreate(BaseModel):
    evaluation_id: int
    product_id: int

class RepaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)

class ClaimCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    amount: Decimal = Field(gt=0)
    note: str = Field(min_length=2, max_length=1000)
    document_id: int | None = None


def scalar_ok(value: Any) -> bool:
    return value is None or type(value) in (str, int, float, bool)

def borrower_for(db: Session, user: User) -> Borrower:
    row = db.scalar(select(Borrower).where(Borrower.user_id == user.id))
    if row is None:
        raise HTTPException(403, "Borrower profile required")
    return row

def authorized_app(db: Session, app_id: int, user: User) -> Application:
    item = db.get(Application, app_id)
    if item is None:
        raise HTTPException(404, "Application not found")
    if user.role in ("platform_admin", "reviewer"):
        return item
    if user.role != "borrower" or borrower_for(db, user).id != item.borrower_id:
        raise HTTPException(403, "Not authorized for application")
    return item

def admin_only(user: User = Depends(roles("platform_admin"))) -> User:
    return user

def rules_for(db: Session, policy_id: int) -> list[dict]:
    rows = db.scalars(select(PolicyRule).where(PolicyRule.policy_id == policy_id).order_by(PolicyRule.id)).all()
    return [{"id": x.id, "field_key": x.field_key, "operator": x.operator, "target": x.target, "required": x.required} for x in rows]

def evidence_for(db: Session, app_id: int):
    facts = list(db.scalars(select(EvidenceFact).where(EvidenceFact.application_id == app_id)).all())
    values = {f.key: f.value for f in facts}
    candidates = {f.key: f.candidates or [] for f in facts if not f.verified}
    versions = {f.key: f.version for f in facts}
    return facts, values, candidates, versions

def save_evaluation(db: Session, item: Application, policy: Policy, user: User, prior: Evaluation | None = None, changed: set[str] | None = None):
    rules = rules_for(db, policy.id)
    facts, values, candidates, versions = evidence_for(db, item.id)
    if prior and changed is not None:
        old = list(db.scalars(select(RuleResult).where(RuleResult.evaluation_id == prior.id)).all())
        previous = [{
            "rule_id": r.rule_id, "field_key": next(x["field_key"] for x in rules if x["id"] == r.rule_id),
            "observed": r.observed, "status": r.status,
            "required": next(x["required"] for x in rules if x["id"] == r.rule_id),
            "explanation": r.explanation,
        } for r in old]
        decision, details = selective_recompute(rules, values, previous, changed)
    else:
        decision, details = evaluate_rules(rules, values)
    stab = stability(rules, values, candidates)
    if prior is None:
        prior = db.scalar(select(Evaluation).where(
            Evaluation.application_id == item.id,
            Evaluation.policy_id == policy.id, Evaluation.is_current.is_(True)
        ))
    if prior:
        prior.is_current = False
    snapshot = Evaluation(
        application_id=item.id, lender_id=policy.lender_id, policy_id=policy.id,
        evidence_versions=versions, decision=decision, stable=stab["stable"], is_current=True
    )
    db.add(snapshot)
    db.flush()
    for detail in details:
        db.add(RuleResult(
            evaluation_id=snapshot.id, rule_id=detail["rule_id"],
            status=detail["status"], observed=detail["observed"],
            explanation=detail["explanation"]
        ))
    audit(db, user, "evaluation.compute", "evaluation", snapshot.id, decision=decision,
          policy_id=policy.id, selective=changed is not None)
    return {"id": snapshot.id, "lender_id": policy.lender_id, "policy_id": policy.id,
            "decision": decision, "stable": stab["stable"], "stability": stab,
            "evidence_versions": versions, "rules": details,
            "label": "Preliminary simulated rules result — NOT a lender approval"}

@router.post("/admin/lenders", status_code=201)
def create_lender(payload: LenderCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    if db.scalar(select(Lender).where(Lender.name == payload.name.strip())):
        raise HTTPException(409, "Lender already exists")
    row = Lender(name=payload.name.strip())
    db.add(row)
    db.flush()
    audit(db, user, "lender.create", "lender", row.id)
    db.commit()
    return {"id": row.id, "name": row.name, "synthetic": True}

@router.get("/lenders")
def list_lenders(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": l.id, "name": l.name} for l in db.scalars(select(Lender).where(Lender.active.is_(True))).all()]

@router.post("/admin/lenders/{lender_id}/users", status_code=201)
def create_lender_user(lender_id: int, payload: LenderUserCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    if not db.get(Lender, lender_id):
        raise HTTPException(404, "Lender not found")
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Account exists")
    acc = User(email=email, password_hash=hash_password(payload.password), role="lender_admin", lender_id=lender_id)
    db.add(acc)
    db.flush()
    audit(db, user, "lender_user.create", "user", acc.id)
    db.commit()
    return {"id": acc.id, "role": acc.role, "lender_id": lender_id}

@router.post("/admin/lenders/{lender_id}/products", status_code=201)
def create_product(lender_id: int, payload: ProductCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    if not db.get(Lender, lender_id):
        raise HTTPException(404, "Lender not found")
    if payload.max_amount < payload.min_amount:
        raise HTTPException(422, "max_amount must be >= min_amount")
    p = LoanProduct(lender_id=lender_id, name=payload.name, min_amount=payload.min_amount,
                    max_amount=payload.max_amount, apr=payload.apr)
    db.add(p)
    db.flush()
    audit(db, user, "product.create", "loan_product", p.id)
    db.commit()
    return {"id": p.id, "lender_id": lender_id, "name": p.name, "apr": p.apr}

@router.get("/products")
def products(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [{"id": p.id, "lender_id": p.lender_id, "name": p.name,
             "min_amount": p.min_amount, "max_amount": p.max_amount, "apr": p.apr}
            for p in db.scalars(select(LoanProduct).where(LoanProduct.active.is_(True))).all()]

@router.post("/admin/lenders/{lender_id}/policies", status_code=201)
def create_policy(lender_id: int, payload: PolicyCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    if not db.get(Lender, lender_id):
        raise HTTPException(404, "Lender not found")
    if not any(r.required for r in payload.rules):
        raise HTTPException(422, "At least one mandatory rule required")
    for r in payload.rules:
        if not scalar_ok(r.target) and not (r.operator == "in" and isinstance(r.target, list) and all(scalar_ok(x) for x in r.target)):
            raise HTTPException(422, "Only scalar targets or scalar lists for 'in' are supported")
        if r.operator == "in" and not isinstance(r.target, list):
            raise HTTPException(422, "Operator 'in' requires a list target")
    earlier = list(db.scalars(select(Policy).where(Policy.lender_id == lender_id).order_by(Policy.version.desc())).all())
    for old in earlier:
        old.active = False
    pol = Policy(lender_id=lender_id, version=(earlier[0].version + 1 if earlier else 1), active=True)
    db.add(pol)
    db.flush()
    for rule in payload.rules:
        row = PolicyRule(policy_id=pol.id, field_key=rule.field_key, operator=rule.operator,
                         target=rule.target, required=rule.required)
        db.add(row)
        db.flush()
        db.add(DependencyEdge(policy_rule_id=row.id, evidence_key=rule.field_key))
    audit(db, user, "policy.publish", "policy", pol.id, version=pol.version)
    db.commit()
    return {"id": pol.id, "lender_id": lender_id, "version": pol.version, "rules": rules_for(db, pol.id)}

@router.get("/lenders/{lender_id}/policies")
def list_policies(lender_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role == "lender_admin" and user.lender_id != lender_id:
        raise HTTPException(403, "Not your lender")
    policies = db.scalars(select(Policy).where(Policy.lender_id == lender_id).order_by(Policy.version.desc())).all()
    return [{"id": p.id, "version": p.version, "active": p.active, "rules": rules_for(db, p.id)} for p in policies]

@router.post("/applications", status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db), user: User = Depends(roles("borrower"))):
    borrower = borrower_for(db, user)
    item = Application(borrower_id=borrower.id, requested_amount=payload.requested_amount,
                       loan_purpose=payload.loan_purpose, status="submitted")
    db.add(item)
    db.flush()
    audit(db, user, "application.create", "application", item.id)
    db.commit()
    return {"id": item.id, "status": item.status, "requested_amount": item.requested_amount}

@router.get("/applications")
def list_applications(db: Session = Depends(get_db), user: User = Depends(roles("borrower", "platform_admin", "reviewer"))):
    stmt = select(Application).order_by(Application.id.desc())
    if user.role == "borrower":
        stmt = stmt.where(Application.borrower_id == borrower_for(db, user).id)
    return [{"id": a.id, "requested_amount": a.requested_amount,
             "loan_purpose": a.loan_purpose, "status": a.status}
            for a in db.scalars(stmt).all()]

@router.get("/applications/{app_id}")
def application_detail(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = authorized_app(db, app_id, user)
    return {"id": a.id, "requested_amount": a.requested_amount,
            "loan_purpose": a.loan_purpose, "status": a.status,
            "borrower_id": a.borrower_id}

@router.post("/applications/{app_id}/documents", status_code=201)
async def upload_document(app_id: int, label: str, file: UploadFile = File(...),
    db: Session = Depends(get_db), user: User = Depends(roles("borrower", "platform_admin"))):
    authorized_app(db, app_id, user)
    data = await file.read(5_000_001)
    if not data or len(data) > 5_000_000:
        raise HTTPException(413, "Document must be between 1 byte and 5MB")
    mime = file.content_type or ""
    signatures = {"application/pdf": data.startswith(b"%PDF-"),
                  "image/png": data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"),
                  "image/jpeg": data.startswith(b"\\xff\\xd8\\xff")}
    if not signatures.get(mime, False):
        raise HTTPException(415, "Only real PDF, PNG and JPEG documents are accepted")
    safe_name = Path(file.filename or "upload").name[:150]
    key = f"{uuid4().hex}"
    folder = Path(get_settings().storage_dir)
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    destination = folder / key
    with open(destination, "xb") as target:
        target.write(data)
    os.chmod(destination, 0o600)
    document = Document(application_id=app_id, label=label[:100], filename=safe_name,
                        mime_type=mime, sha256=sha256(data).hexdigest(), storage_key=key)
    db.add(document)
    db.flush()
    audit(db, user, "document.upload", "document", document.id, sha256=document.sha256)
    db.commit()
    return {"id": document.id, "sha256": document.sha256, "extraction_mode": "manual_only",
            "notice": "OCR is not executed. Supply explicitly labelled candidate evidence."}

@router.get("/applications/{app_id}/documents")
def list_documents(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    return [{"id": d.id, "label": d.label, "filename": d.filename, "sha256": d.sha256}
            for d in db.scalars(select(Document).where(Document.application_id == app_id)).all()]

@router.get("/applications/{app_id}/documents/{document_id}/download")
def download_document(app_id: int, document_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    doc = db.get(Document, document_id)
    if doc is None or doc.application_id != app_id:
        raise HTTPException(404, "Document not found")
    path = Path(get_settings().storage_dir) / doc.storage_key
    if not path.is_file():
        raise HTTPException(404, "File unavailable")
    return FileResponse(path, media_type=doc.mime_type, filename=doc.filename)

@router.post("/applications/{app_id}/evidence", status_code=201)
def set_evidence(app_id: int, payload: EvidenceCreate, db: Session = Depends(get_db),
                 user: User = Depends(roles("borrower", "platform_admin"))):
    authorized_app(db, app_id, user)
    if not scalar_ok(payload.value) or not all(scalar_ok(v) for v in payload.candidates):
        raise HTTPException(422, "Evidence values must be JSON scalars")
    if payload.document_id is not None:
        doc = db.get(Document, payload.document_id)
        if not doc or doc.application_id != app_id:
            raise HTTPException(422, "Document must belong to this application")
    existing = db.scalar(select(EvidenceFact).where(EvidenceFact.application_id == app_id, EvidenceFact.key == payload.key))
    if existing:
        raise HTTPException(409, "Evidence key exists; request verification or revision instead")
    fact = EvidenceFact(application_id=app_id, key=payload.key, value=payload.value,
                        candidates=payload.candidates, verified=False,
                        document_id=payload.document_id, version=1)
    db.add(fact)
    db.flush()
    db.add(EvidenceRevision(fact_id=fact.id, version=1, value=fact.value,
                            candidates=fact.candidates, verified=False, actor_id=user.id))
    audit(db, user, "evidence.create", "evidence_fact", fact.id, key=fact.key)
    db.commit()
    return {"id": fact.id, "key": fact.key, "version": fact.version,
            "verified": False, "source_document_id": fact.document_id}

@router.get("/applications/{app_id}/evidence")
def list_evidence(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    facts, _, _, _ = evidence_for(db, app_id)
    return [{"id": f.id, "key": f.key, "value": f.value, "candidates": f.candidates,
             "verified": f.verified, "version": f.version, "document_id": f.document_id} for f in facts]

@router.get("/applications/{app_id}/evidence/{fact_id}/history")
def fact_history(app_id: int, fact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    fact = db.get(EvidenceFact, fact_id)
    if not fact or fact.application_id != app_id:
        raise HTTPException(404, "Fact not found")
    return [{"version": r.version, "value": r.value, "candidates": r.candidates,
             "verified": r.verified, "actor_id": r.actor_id}
            for r in db.scalars(select(EvidenceRevision).where(EvidenceRevision.fact_id == fact_id).order_by(EvidenceRevision.version)).all()]

@router.post("/applications/{app_id}/evaluate")
def evaluate_application(app_id: int, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    a = authorized_app(db, app_id, user)
    policies = db.scalars(select(Policy).where(Policy.active.is_(True)).order_by(Policy.lender_id)).all()
    if not policies:
        raise HTTPException(409, "No active fictional lender policies configured")
    decisions = [save_evaluation(db, a, p, user) for p in policies]
    audit(db, user, "application.evaluate", "application", a.id, lender_count=len(decisions))
    db.commit()
    return {"application_id": a.id, "decisions": decisions}

@router.get("/applications/{app_id}/evaluations")
def get_evaluations(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    rows = db.scalars(select(Evaluation).where(Evaluation.application_id == app_id).order_by(Evaluation.id.desc())).all()
    return [{"id": e.id, "lender_id": e.lender_id, "policy_id": e.policy_id,
             "decision": e.decision, "stable": e.stable,
             "current": e.is_current, "evidence_versions": e.evidence_versions,
             "rules": [{"rule_id": r.rule_id, "status": r.status, "observed": r.observed,
                        "explanation": r.explanation}
                       for r in db.scalars(select(RuleResult).where(RuleResult.evaluation_id == e.id)).all()]}
            for e in rows]

@router.get("/applications/{app_id}/counterfactual")
def get_counterfactual(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    facts, values, candidates, _ = evidence_for(db, app_id)
    policies = db.scalars(select(Policy).where(Policy.active.is_(True))).all()
    return [{"lender_id": p.lender_id, "policy_id": p.id, **stability(rules_for(db, p.id), values, candidates)}
            for p in policies]

@router.post("/applications/{app_id}/schedule-review")
def schedule_review(app_id: int, db: Session = Depends(get_db),
                    user: User = Depends(roles("platform_admin", "reviewer"))):
    authorized_app(db, app_id, user)
    facts, values, candidates, _ = evidence_for(db, app_id)
    policies = db.scalars(select(Policy).where(Policy.active.is_(True))).all()
    scores = {}
    for f in facts:
        if f.verified:
            continue
        dependent = 0
        changed_lenders = 0
        for p in policies:
            rules = rules_for(db, p.id)
            linked = [r for r in rules if r["field_key"] == f.key]
            dependent += len(linked)
            if linked:
                b = stability(rules, values, {f.key: candidates.get(f.key, [])})
                if b["stable"] is False or b["stable"] is None:
                    changed_lenders += 1
        if not dependent:
            continue
        scores[f.id] = review_priority(changed_lenders, dependent, bool(f.candidates))
    created = []
    for fact_id, score in sorted(scores.items(), key=lambda item: -item[1]):
        existing = db.scalar(select(ReviewTask).where(ReviewTask.fact_id == fact_id, ReviewTask.status == "open"))
        if existing:
            continue
        task = ReviewTask(application_id=app_id, fact_id=fact_id, priority=score,
                          reason="Evidence may affect preliminary lender rules; verify source")
        db.add(task)
        db.flush()
        created.append(task.id)
        audit(db, user, "review.schedule", "review_task", task.id, priority=score)
    db.commit()
    return {"created_task_ids": created, "ranked_fact_ids": list(scores.keys())}

@router.get("/review/tasks")
def review_tasks(db: Session = Depends(get_db), user: User = Depends(roles("platform_admin", "reviewer"))):
    rows = db.scalars(select(ReviewTask).where(ReviewTask.status == "open").order_by(ReviewTask.priority.desc(), ReviewTask.id)).all()
    return [{"id": t.id, "application_id": t.application_id, "fact_id": t.fact_id,
             "priority": t.priority, "reason": t.reason, "status": t.status} for t in rows]

@router.post("/review/tasks/{task_id}/verify")
def verify_evidence(task_id: int, payload: EvidenceVerify, db: Session = Depends(get_db),
                    user: User = Depends(roles("platform_admin", "reviewer"))):
    task = db.get(ReviewTask, task_id)
    if not task or task.status != "open":
        raise HTTPException(404, "Open task not found")
    if not scalar_ok(payload.value) or payload.value is None:
        raise HTTPException(422, "Verified value must be a non-null scalar")
    fact = db.get(EvidenceFact, task.fact_id)
    fact.version += 1
    fact.value = payload.value
    fact.candidates = []
    fact.verified = True
    fact.updated_at = datetime.now(timezone.utc)
    db.add(EvidenceRevision(fact_id=fact.id, version=fact.version, value=fact.value,
                            candidates=[], verified=True, actor_id=user.id))
    other_tasks = db.scalars(select(ReviewTask).where(ReviewTask.fact_id == fact.id, ReviewTask.status == "open")).all()
    for t in other_tasks:
        t.status = "resolved"
        t.assigned_to = user.id
    changed = {fact.key}
    old_evals = db.scalars(select(Evaluation).where(
        Evaluation.application_id == task.application_id, Evaluation.is_current.is_(True)
    )).all()
    recomputed = []
    for evaluation in old_evals:
        related = db.scalar(select(DependencyEdge.id).join(PolicyRule, DependencyEdge.policy_rule_id == PolicyRule.id)
                            .where(PolicyRule.policy_id == evaluation.policy_id,
                                   DependencyEdge.evidence_key == fact.key))
        if related is None:
            continue
        result = save_evaluation(db, db.get(Application, task.application_id),
                                 db.get(Policy, evaluation.policy_id), user,
                                 prior=evaluation, changed=changed)
        recomputed.append(result)
    audit(db, user, "evidence.verify", "evidence_fact", fact.id,
          version=fact.version, note=payload.note, selectively_recomputed=len(recomputed))
    db.commit()
    return {"fact_id": fact.id, "verified_version": fact.version,
            "recomputed": recomputed, "history_preserved": True}

@router.post("/applications/{app_id}/offers", status_code=201)
def create_offer(app_id: int, payload: OfferCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    item = authorized_app(db, app_id, user)
    ev = db.get(Evaluation, payload.evaluation_id)
    product = db.get(LoanProduct, payload.product_id)
    if not ev or not ev.is_current or ev.application_id != app_id or ev.decision != PASS or ev.stable is not True:
        raise HTTPException(409, "Current, stable preliminary PASS evaluation required")
    if not product or not product.active or product.lender_id != ev.lender_id:
        raise HTTPException(422, "Product/lender mismatch")
    if not product.min_amount <= item.requested_amount <= product.max_amount:
        raise HTTPException(422, "Requested loan amount outside product limits")
    required_keys = {r["field_key"] for r in rules_for(db, ev.policy_id) if r["required"]}
    facts, _, _, _ = evidence_for(db, app_id)
    if not required_keys.issubset({f.key for f in facts if f.verified}):
        raise HTTPException(409, "Required evidence must be verified before generating a provisional offer")
    o = LoanOffer(application_id=app_id, lender_id=ev.lender_id, product_id=product.id,
                  evaluation_id=ev.id, amount=item.requested_amount, apr=product.apr, status="provisional")
    db.add(o)
    db.flush()
    audit(db, user, "offer.simulate", "loan_offer", o.id)
    db.commit()
    return {"id": o.id, "status": "provisional", "simulation": True, "amount": o.amount, "apr": o.apr}

def offer_owned(db: Session, offer: LoanOffer, user: User):
    authorized_app(db, offer.application_id, user)

@router.get("/applications/{app_id}/offers")
def get_offers(app_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_app(db, app_id, user)
    return [{"id": o.id, "lender_id": o.lender_id, "amount": o.amount, "apr": o.apr, "status": o.status,
             "simulation": True}
            for o in db.scalars(select(LoanOffer).where(LoanOffer.application_id == app_id)).all()]

@router.get("/offers/{offer_id}/agreement")
def agreement(offer_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    offer = db.get(LoanOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer_owned(db, offer, user)
    return {"offer_id": offer.id, "text": f"DEMO AGREEMENT ONLY. No legally enforceable offer. Simulated amount: INR {offer.amount}; APR: {offer.apr}%. No real lender consent or funds transfer.", "legally_binding": False}

@router.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: int, db: Session = Depends(get_db), user: User = Depends(roles("borrower"))):
    offer = db.get(LoanOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer_owned(db, offer, user)
    if offer.status != "provisional":
        raise HTTPException(409, "Offer not available for simulated acceptance")
    offer.status = "accepted"
    loan = Loan(offer_id=offer.id, status="accepted")
    db.add(loan)
    db.flush()
    audit(db, user, "offer.accept_demo", "loan", loan.id)
    db.commit()
    return {"loan_id": loan.id, "status": loan.status, "simulation": True}

@router.post("/loans/{loan_id}/mock-disburse")
def mock_disburse(loan_id: int, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    loan = db.get(Loan, loan_id)
    if not loan or loan.status != "accepted":
        raise HTTPException(409, "Loan must be in accepted simulated state")
    loan.status = "mock_disbursed"
    loan.disbursed_at = datetime.now(timezone.utc)
    audit(db, user, "loan.mock_disburse", "loan", loan.id)
    db.commit()
    return {"loan_id": loan.id, "status": loan.status, "money_transferred": False}

@router.post("/loans/{loan_id}/mock-repayments", status_code=201)
def mock_repayment(loan_id: int, payload: RepaymentCreate, db: Session = Depends(get_db),
                   user: User = Depends(admin_only)):
    loan = db.get(Loan, loan_id)
    if not loan or loan.status != "mock_disbursed":
        raise HTTPException(409, "Simulated loan is not disbursed")
    payment = Repayment(loan_id=loan.id, amount=payload.amount, reference=f"DEMO-{uuid4().hex[:12]}")
    db.add(payment)
    db.flush()
    audit(db, user, "loan.mock_repayment", "repayment", payment.id)
    db.commit()
    return {"id": payment.id, "amount": payment.amount, "simulation": True, "money_moved": False}

def authorized_loan(db: Session, loan_id: int, user: User) -> tuple[Loan, LoanOffer]:
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, "Loan not found")
    offer = db.get(LoanOffer, loan.offer_id)
    authorized_app(db, offer.application_id, user)
    return loan, offer

@router.post("/loans/{loan_id}/utilization", status_code=201)
def utilization_claim(loan_id: int, payload: ClaimCreate, db: Session = Depends(get_db),
                      user: User = Depends(roles("borrower", "platform_admin"))):
    loan, offer = authorized_loan(db, loan_id, user)
    if loan.status != "mock_disbursed":
        raise HTTPException(409, "Utilization claims require a simulated disbursement")
    if payload.document_id is not None:
        document = db.get(Document, payload.document_id)
        if not document or document.application_id != offer.application_id:
            raise HTTPException(422, "Evidence document does not belong to this loan application")
    claim = UtilizationClaim(loan_id=loan_id, category=payload.category, amount=payload.amount,
                             note=payload.note, status="unverified")
    db.add(claim)
    db.flush()
    if payload.document_id:
        db.add(UtilizationLink(claim_id=claim.id, document_id=payload.document_id, annotation="Submitted supporting evidence"))
    audit(db, user, "utilization.claim", "utilization_claim", claim.id)
    db.commit()
    return {"claim_id": claim.id, "status": claim.status, "fraud_determination": None}

@router.get("/loans/{loan_id}/utilization")
def utilization_list(loan_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    authorized_loan(db, loan_id, user)
    claims = db.scalars(select(UtilizationClaim).where(UtilizationClaim.loan_id == loan_id)).all()
    return [{"id": c.id, "category": c.category, "amount": c.amount, "note": c.note,
             "status": c.status, "links": [{"document_id": l.document_id, "annotation": l.annotation}
             for l in db.scalars(select(UtilizationLink).where(UtilizationLink.claim_id == c.id)).all()]}
            for c in claims]
