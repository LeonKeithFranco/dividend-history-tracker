"""increase dividend precision to 6 decimal places

Revision ID: 0afe53e1bbc7
Revises: cb7c6c3f2302
Create Date: 2026-10-02 19:59:11.535995

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0afe53e1bbc7"
down_revision: Union[str, Sequence[str], None] = "cb7c6c3f2302"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "cash_amount",
            existing_type=sa.NUMERIC(precision=10, scale=2),
            type_=sa.Numeric(precision=10, scale=6),
            existing_nullable=False,
        )

    with op.batch_alter_table("metrics", schema=None) as batch_op:
        batch_op.alter_column(
            "annual_dividend",
            existing_type=sa.NUMERIC(precision=10, scale=2),
            type_=sa.Numeric(precision=10, scale=6),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("metrics", schema=None) as batch_op:
        batch_op.alter_column(
            "annual_dividend",
            existing_type=sa.Numeric(precision=10, scale=6),
            type_=sa.NUMERIC(precision=10, scale=2),
            existing_nullable=False,
        )

    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.alter_column(
            "cash_amount",
            existing_type=sa.Numeric(precision=10, scale=6),
            type_=sa.NUMERIC(precision=10, scale=2),
            existing_nullable=False,
        )
