"""Provision an administrative account securely, with an interactive password prompt.

Run: python -m app.cli create-admin admin@example.org
"""
import getpass
import sys
from sqlalchemy import select
from app.db import get_engine, Base
from app.models import User
from app.security import hash_password
from sqlalchemy.orm import Session

def main():
    if len(sys.argv) != 3 or sys.argv[1] != "create-admin":
        raise SystemExit("Usage: python -m app.cli create-admin EMAIL")
    email = sys.argv[2].strip().lower()
    pwd = getpass.getpass("New admin password (12+ characters): ")
    if len(pwd) < 12:
        raise SystemExit("Password too short")
    with Session(get_engine()) as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists")
        user = User(email=email, password_hash=hash_password(pwd), role="platform_admin")
        db.add(user)
        db.commit()
        print("Administrator created:", email)

if __name__ == "__main__":
    main()
