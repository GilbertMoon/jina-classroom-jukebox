"""Create the initial jukebox schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def uuid_column() -> sa.Column:
    return sa.Column("id", sa.Uuid(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        uuid_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tracks",
        uuid_column(),
        sa.Column("youtube_video_id", sa.String(20)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("artist_or_channel", sa.String(300)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("thumbnail_url", sa.String(2048)),
        sa.Column("media_status", sa.String(32), nullable=False),
        sa.Column("media_path", sa.String(1024)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("rights_status", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tracks"),
        sa.UniqueConstraint("youtube_video_id", name="uq_tracks_youtube_video_id"),
        sa.UniqueConstraint("sha256", name="uq_tracks_sha256"),
    )

    op.create_table(
        "playlists",
        uuid_column(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_playlists_created_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_playlists"),
        sa.UniqueConstraint("name", name="uq_playlists_name"),
    )

    op.create_table(
        "requests",
        uuid_column(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reject_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_requests_user_id_users"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], name="fk_requests_track_id_tracks"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_requests_reviewed_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_requests"),
    )
    op.create_index("ix_requests_user_id", "requests", ["user_id"])
    op.create_index("ix_requests_track_id", "requests", ["track_id"])

    op.create_table(
        "playlist_items",
        uuid_column(),
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], name="fk_playlist_items_playlist_id_playlists"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], name="fk_playlist_items_track_id_tracks"),
        sa.PrimaryKeyConstraint("id", name="pk_playlist_items"),
        sa.UniqueConstraint("playlist_id", "position", name="uq_playlist_items_playlist_id"),
    )

    op.create_table(
        "schedules",
        uuid_column(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False),
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], name="fk_schedules_playlist_id_playlists"),
        sa.PrimaryKeyConstraint("id", name="pk_schedules"),
    )

    op.create_table(
        "playback_events",
        uuid_column(),
        sa.Column("track_id", sa.Uuid()),
        sa.Column("schedule_id", sa.Uuid()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("result", sa.String(50), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], name="fk_playback_events_track_id_tracks"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], name="fk_playback_events_schedule_id_schedules"),
        sa.PrimaryKeyConstraint("id", name="pk_playback_events"),
    )

    op.create_table(
        "control_audit_logs",
        uuid_column(),
        sa.Column("admin_id", sa.Uuid()),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], name="fk_control_audit_logs_admin_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_control_audit_logs"),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_system_settings"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("control_audit_logs")
    op.drop_table("playback_events")
    op.drop_table("schedules")
    op.drop_table("playlist_items")
    op.drop_index("ix_requests_track_id", table_name="requests")
    op.drop_index("ix_requests_user_id", table_name="requests")
    op.drop_table("requests")
    op.drop_table("playlists")
    op.drop_table("tracks")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
