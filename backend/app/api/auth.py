"""Borrower self-registration; platform administrators are provisioned via CLI."""
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Borrower
from app.security import hash_password, verify_password, create_token, current_user, audit

router = APIRouter(prefix="/api/v1/auth", tags=["identity"])

class Registration(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    legal_name: str = Field(min_length=2, max_length=150)
    borrower_type: str = Field(default="fpo", pattern="^(farmer|fpo|business)$")

class Login(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=201)
def register(payload: Registration, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "Invalid email")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Account already exists")
    user = User(email=email, password_hash=hash_password(payload.password), role="borrower")
    db.add(user)
    db.flush()
    db.add(Borrower(user_id=user.id, legal_name=payload.legal_name, borrower_type=payload.borrower_type))
    audit(db, user, "identity.register", "user", user.id)
    db.commit()
    return {"id": user.id, "email": user.email, "role": user.role}

@router.post("/login")
def login(payload: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect credentials")
    return {"access_token": create_token(user), "token_type": "bearer"}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role, "lender_id": user.lender_id}
