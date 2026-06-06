from collections.abc import Sequence

from alembic import op

revision: str = "8b2c3d4e5f6a"
down_revision: str | None = "7a1d2e3f4b5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_entry_profile_artifacts_entry_id'
            ) THEN
                ALTER TABLE entry_profile_artifacts
                ADD CONSTRAINT uq_entry_profile_artifacts_entry_id UNIQUE (entry_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_user_profile_artifacts_user_id'
            ) THEN
                ALTER TABLE user_profile_artifacts
                ADD CONSTRAINT uq_user_profile_artifacts_user_id UNIQUE (user_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_restaurant_profile_artifacts_restaurant_id'
            ) THEN
                ALTER TABLE restaurant_profile_artifacts
                ADD CONSTRAINT uq_restaurant_profile_artifacts_restaurant_id UNIQUE (restaurant_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    pass
