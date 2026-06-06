from collections.abc import Sequence

from alembic import op

revision: str = "9c3d4e5f6a7b"
down_revision: str | None = "8b2c3d4e5f6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS taste_jobs (
            created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp(0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp(0),
            id VARCHAR NOT NULL PRIMARY KEY,
            user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            state VARCHAR NOT NULL,
            started_at TIMESTAMPTZ NULL,
            finished_at TIMESTAMPTZ NULL,
            error VARCHAR NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_taste_jobs_active_user_id
        ON taste_jobs (user_id)
        WHERE state IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    pass
