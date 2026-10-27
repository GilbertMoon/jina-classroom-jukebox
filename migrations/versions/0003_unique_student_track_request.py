"""Prevent duplicate requests for the same student and track.

Revision ID: 0003
Revises: 0002
"""

from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("requests") as batch_op:
        batch_op.create_unique_constraint(
            "uq_requests_user_id_track_id", ["user_id", "track_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("requests") as batch_op:
        batch_op.drop_constraint("uq_requests_user_id_track_id", type_="unique")
