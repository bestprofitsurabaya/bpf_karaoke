"""Initial schema - bootstrap dari metadata model (idempotent)

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-07

Migration bootstrap ini memakai Base.metadata.create_all(), yang bersifat
idempotent: pada database lama yang sudah punya tabel, create_all hanya
no-op lalu Alembic men-stamp versi 0001. Untuk perubahan skema berikutnya,
gunakan migration op.create_table/op.add_column, dst.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Import Base & models agar metadata lengkap
    from database import Base
    import models  # noqa: F401
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    # Hapus tabel dalam urutan dependensi terbalik
    bind.execute(sa.text("DROP TABLE IF EXISTS operator_favorites CASCADE"))
    bind.execute(sa.text("DROP TABLE IF EXISTS playback_history CASCADE"))
    bind.execute(sa.text("DROP TABLE IF EXISTS queue CASCADE"))
    bind.execute(sa.text("DROP TABLE IF EXISTS rooms CASCADE"))
    bind.execute(sa.text("DROP TABLE IF EXISTS users CASCADE"))
    bind.execute(sa.text("DROP TABLE IF EXISTS songs CASCADE"))
