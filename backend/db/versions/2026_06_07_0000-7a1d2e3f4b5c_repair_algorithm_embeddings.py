from collections.abc import Sequence

from alembic import op

revision: str = "7a1d2e3f4b5c"
down_revision: str | None = "4c2f6f9b8a1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE user_profile_artifacts "
        "ADD COLUMN IF NOT EXISTS long_term_embedding vector(1024)"
    )
    op.execute(
        "ALTER TABLE user_profile_artifacts "
        "ADD COLUMN IF NOT EXISTS short_term_embedding vector(1024)"
    )
    op.execute(
        "ALTER TABLE restaurant_profile_artifacts ADD COLUMN IF NOT EXISTS embedding vector(1024)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_restaurant_profile_artifacts_embedding_hnsw "
        "ON restaurant_profile_artifacts USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    pass
