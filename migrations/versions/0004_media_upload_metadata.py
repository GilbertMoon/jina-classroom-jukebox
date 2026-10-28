"""Add metadata for authorized local media uploads.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("rights_note", sa.String(500)))
    op.add_column("tracks", sa.Column("media_original_filename", sa.String(255)))
    op.add_column("tracks", sa.Column("media_content_type", sa.String(100)))
    op.add_column("tracks", sa.Column("media_size_bytes", sa.BigInteger()))


def downgrade() -> None:
    op.drop_column("tracks", "media_size_bytes")
    op.drop_column("tracks", "media_content_type")
    op.drop_column("tracks", "media_original_filename")
    op.drop_column("tracks", "rights_note")
