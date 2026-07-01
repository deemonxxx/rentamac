"""add_rustdesk_fields

Revision ID: a1b2c3d4e5f6
Revises: 0102a1c559c2
Create Date: 2026-06-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0102a1c559c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add RustDesk and SSH fields to nodes table."""
    op.add_column("nodes", sa.Column("rustdesk_id", sa.String(20), nullable=True))
    op.create_index("ix_nodes_rustdesk_id", "nodes", ["rustdesk_id"])
    op.add_column("nodes", sa.Column("rustdesk_password", sa.String(100), nullable=True))
    op.add_column("nodes", sa.Column("ssh_port", sa.Integer(), nullable=False, server_default="22"))


def downgrade() -> None:
    """Remove RustDesk and SSH fields from nodes table."""
    op.drop_column("nodes", "ssh_port")
    op.drop_column("nodes", "rustdesk_password")
    op.drop_index("ix_nodes_rustdesk_id", table_name="nodes")
    op.drop_column("nodes", "rustdesk_id")
