"""Add room_sessions table

Revision ID: 0002_room_sessions
Revises: 0001_initial
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_room_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "room_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_room_sessions_room_id", "room_sessions", ["room_id"])
    op.create_index("ix_room_sessions_status", "room_sessions", ["status"])
    # Partial unique index: satu sesi aktif per room
    op.create_index(
        "uq_room_sessions_active", "room_sessions", ["room_id"],
        unique=True, postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_room_sessions_active", table_name="room_sessions")
    op.drop_index("ix_room_sessions_status", table_name="room_sessions")
    op.drop_index("ix_room_sessions_room_id", table_name="room_sessions")
    op.drop_table("room_sessions")
