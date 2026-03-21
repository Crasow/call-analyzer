"""extract parsed JSON from legacy Gemini API responses in profile_results.data

Revision ID: 005
Revises: 004
Create Date: 2026-03-22
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _extract_parsed(raw: dict) -> dict:
    """Extract parsed model JSON from raw Gemini API response."""
    if "candidates" in raw:
        try:
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError):
            return raw
    return raw


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, data FROM profile_results")).fetchall()
    for row_id, data in rows:
        if data and "candidates" in data:
            parsed = _extract_parsed(data)
            conn.execute(
                sa.text("UPDATE profile_results SET data = :data, transcript = :transcript WHERE id = :id"),
                {"data": json.dumps(parsed), "id": row_id, "transcript": parsed.get("transcript")},
            )


def downgrade() -> None:
    pass  # Cannot restore original Gemini API wrapper
