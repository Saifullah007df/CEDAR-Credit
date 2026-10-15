"""Add simulated repayment installment schedule.

Revision ID: 0003_repayment
Revises: 0002_extractions
"""
from alembic import op
from app.models import RepaymentSchedule

revision = "0003_repayment"
down_revision = "0002_extractions"
branch_labels = None
depends_on = None

def upgrade():
    RepaymentSchedule.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade():
    RepaymentSchedule.__table__.drop(bind=op.get_bind(), checkfirst=True)
