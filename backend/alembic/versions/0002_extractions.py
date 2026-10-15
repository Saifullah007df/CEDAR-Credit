"""Add optional extraction provenance, idempotent with original metadata baseline.

Revision ID: 0002_extractions
Revises: 0001_baseline
"""
from alembic import op
from app.models import DocumentExtraction

revision = "0002_extractions"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

def upgrade():
    DocumentExtraction.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade():
    DocumentExtraction.__table__.drop(bind=op.get_bind(), checkfirst=True)
