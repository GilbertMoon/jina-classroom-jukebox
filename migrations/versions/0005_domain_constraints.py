"""Add database-level domain constraints.

Revision ID: 0005
Revises: 0004
"""

from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.create_check_constraint(
            "ck_tracks_duration_seconds_non_negative",
            "duration_seconds IS NULL OR duration_seconds >= 0",
        )
        batch_op.create_check_constraint(
            "ck_tracks_media_size_bytes_non_negative",
            "media_size_bytes IS NULL OR media_size_bytes >= 0",
        )

    with op.batch_alter_table("playlist_items") as batch_op:
        batch_op.create_check_constraint(
            "ck_playlist_items_position_positive", "position >= 1"
        )

    with op.batch_alter_table("schedules") as batch_op:
        batch_op.create_check_constraint(
            "ck_schedules_volume_range", "volume >= 0 AND volume <= 100"
        )
        batch_op.create_check_constraint(
            "ck_schedules_time_range", "start_time < end_time"
        )

    with op.batch_alter_table("playback_events") as batch_op:
        batch_op.create_check_constraint(
            "ck_playback_events_time_order",
            "ended_at IS NULL OR ended_at >= started_at",
        )


def downgrade() -> None:
    with op.batch_alter_table("playback_events") as batch_op:
        batch_op.drop_constraint(
            "ck_playback_events_time_order", type_="check"
        )

    with op.batch_alter_table("schedules") as batch_op:
        batch_op.drop_constraint("ck_schedules_time_range", type_="check")
        batch_op.drop_constraint("ck_schedules_volume_range", type_="check")

    with op.batch_alter_table("playlist_items") as batch_op:
        batch_op.drop_constraint(
            "ck_playlist_items_position_positive", type_="check"
        )

    with op.batch_alter_table("tracks") as batch_op:
        batch_op.drop_constraint(
            "ck_tracks_media_size_bytes_non_negative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_tracks_duration_seconds_non_negative", type_="check"
        )
