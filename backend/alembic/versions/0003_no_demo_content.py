"""Boards start empty: remove the demo people and everything they posted.

Every user is now a real student, so `is_demo` goes and `platform_user_id`
becomes required. The downgrade restores the columns, not the demo content.

Revision ID: 0003_no_demo_content
Revises: 0002_card_date_unix_time
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_no_demo_content"
down_revision: str | None = "0002_card_date_unix_time"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Their cards, votes and comments (and votes on their cards) go by cascade.
    op.execute("DELETE FROM users WHERE is_demo")
    op.drop_column("users", "is_demo")
    op.alter_column("users", "platform_user_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    op.alter_column("users", "platform_user_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column(
        "users", sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
