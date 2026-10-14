"""Initial normalized CEDAR schema (all future module tables reserved at baseline).

Revision ID: 0001_baseline
Revises:
"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # This baseline creates a fixed catalog of initial tables in dependency order.
    # Subsequent changes require additional explicit Alembic revisions.
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
