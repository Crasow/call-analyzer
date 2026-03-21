"""add profile_results table and migrate profile data

Revision ID: 004
Revises: 003
Create Date: 2026-03-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profile_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Data migration: move profile-based analysis_results into profile_results
    op.execute("""
        INSERT INTO profile_results (id, call_id, data, transcript, analyzed_at)
        SELECT ar.id, ar.call_id, ar.raw_response, ar.transcript, ar.analyzed_at
        FROM analysis_results ar
        JOIN calls c ON c.id = ar.call_id
        WHERE c.profile_id IS NOT NULL
          AND ar.raw_response IS NOT NULL
    """)

    op.execute("""
        DELETE FROM analysis_results
        WHERE call_id IN (
            SELECT id FROM calls WHERE profile_id IS NOT NULL
        )
    """)


def downgrade() -> None:
    # Move profile_results back to analysis_results with dummy fraud fields
    op.execute("""
        INSERT INTO analysis_results (id, call_id, transcript, is_fraud, fraud_score, fraud_categories, reasons, raw_response, analyzed_at)
        SELECT id, call_id, transcript, false, 0.0, '[]'::jsonb, '[]'::jsonb, data, analyzed_at
        FROM profile_results
    """)

    op.drop_table("profile_results")
