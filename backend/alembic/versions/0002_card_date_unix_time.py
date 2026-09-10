"""Card dates become Unix time in seconds instead of calendar dates.

Revision ID: 0002_card_date_unix_time
Revises: 0001_initial
Create Date: 2026-09-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_card_date_unix_time"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A calendar day becomes its midnight, UTC.
    op.alter_column(
        "cards",
        "date",
        existing_type=sa.Date(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using='extract(epoch from "date")::bigint',
    )


def downgrade() -> None:
    op.alter_column(
        "cards",
        "date",
        existing_type=sa.BigInteger(),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="""(to_timestamp("date") AT TIME ZONE 'UTC')::date""",
    )
