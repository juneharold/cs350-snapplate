from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3d7a6f8c9b2e"
down_revision: str | None = "4c2f6f9b8a1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_recommendation_exposure_user_shown_at",
        "recommendation_exposure",
        ["user_id", sa.text("shown_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendation_exposure_user_shown_at",
        table_name="recommendation_exposure",
    )
