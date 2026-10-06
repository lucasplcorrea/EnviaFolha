"""add_name_id_to_employees

Revision ID: b2f7d9a8c1e4
Revises: 6f7c6d04b646
Create Date: 2026-04-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2f7d9a8c1e4"
down_revision: Union[str, Sequence[str], None] = "400a511daf81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("employees", sa.Column("name_id", sa.String(length=255), nullable=True))
    op.create_index("idx_employees_name_id", "employees", ["name_id"], unique=False)
    op.execute(
        sa.text(
            "COMMENT ON COLUMN employees.name_id IS "
            "'Chave auxiliar: company_code + registration_number (5 dig) + normalized_name'"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_employees_name_id", table_name="employees")
    op.drop_column("employees", "name_id")