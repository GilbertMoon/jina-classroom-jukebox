"""Add student wish list items.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wish_list_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_wish_list_items_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], name="fk_wish_list_items_track_id_tracks"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_wish_list_items"),
        sa.UniqueConstraint(
            "user_id", "track_id", name="uq_wish_list_user_track"
        ),
    )
    op.create_index("ix_wish_list_items_user_id", "wish_list_items", ["user_id"])
    op.create_index("ix_wish_list_items_track_id", "wish_list_items", ["track_id"])


def downgrade() -> None:
    op.drop_index("ix_wish_list_items_track_id", table_name="wish_list_items")
    op.drop_index("ix_wish_list_items_user_id", table_name="wish_list_items")
    op.drop_table("wish_list_items")
