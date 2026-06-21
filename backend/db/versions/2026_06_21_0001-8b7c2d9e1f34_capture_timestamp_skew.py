from collections.abc import Sequence

from alembic import op

revision: str = "8b7c2d9e1f34"
down_revision: str | None = "3d7a6f8c9b2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_draft_captured_at_not_future", "drafts", type_="check")
    op.create_check_constraint(
        "ck_draft_captured_at_not_future",
        "drafts",
        "captured_at <= now() + interval '60 seconds'",
    )
    op.drop_constraint("ck_entry_captured_at_not_future", "entries", type_="check")
    op.create_check_constraint(
        "ck_entry_captured_at_not_future",
        "entries",
        "captured_at <= now() + interval '60 seconds'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_draft_captured_at_not_future", "drafts", type_="check")
    op.create_check_constraint(
        "ck_draft_captured_at_not_future",
        "drafts",
        "captured_at <= now()",
    )
    op.drop_constraint("ck_entry_captured_at_not_future", "entries", type_="check")
    op.create_check_constraint(
        "ck_entry_captured_at_not_future",
        "entries",
        "captured_at <= now()",
    )
