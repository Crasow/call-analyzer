"""add performance indexes

Revision ID: 006
Revises: 005
Create Date: 2026-03-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_calls_status", "calls", ["status"])
    op.create_index("ix_calls_profile_id", "calls", ["profile_id"])
    op.create_index("ix_calls_created_at", "calls", ["created_at"])
    op.create_index("ix_analysis_results_call_id", "analysis_results", ["call_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_results_call_id", table_name="analysis_results")
    op.drop_index("ix_calls_created_at", table_name="calls")
    op.drop_index("ix_calls_profile_id", table_name="calls")
    op.drop_index("ix_calls_status", table_name="calls")
