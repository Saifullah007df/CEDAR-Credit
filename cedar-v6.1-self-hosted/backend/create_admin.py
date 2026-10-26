"""Explicit first-administrator creation. Does not create demo users."""
import os, sys,base64,secrets
from sqlalchemy import select
from backend.app import SessionLocal, User,ph

def main():
    username=os.getenv('CEDAR_ADMIN_USERNAME','admin').strip()
    password=os.getenv('CEDAR_ADMIN_PASSWORD','')
    if len(password)<16 or len(set(password))<8:
        raise SystemExit('CEDAR_ADMIN_PASSWORD must be at least 16 chars with eight distinct characters')
    with SessionLocal() as s:
        if s.scalar(select(User).where(User.username==username)):
            raise SystemExit('User already exists; refusing to overwrite credentials')
        secret=base64.b32encode(secrets.token_bytes(20)).decode('ascii')
        s.add(User(username=username,role='admin',password_hash=ph.hash(password),totp_secret=secret))
        s.commit()
    print('Administrator created. Remove bootstrap password from environment.')
    print('ONE-TIME OFFLINE MFA ENROLLMENT KEY (keep private):',secret)
    print('Provision the key as a standard TOTP token in an offline-capable authenticator.')
if __name__=='__main__':main()
