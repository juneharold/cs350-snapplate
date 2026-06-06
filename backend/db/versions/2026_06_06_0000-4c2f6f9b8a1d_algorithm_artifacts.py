from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from pgvector.sqlalchemy import VECTOR

revision: str = "4c2f6f9b8a1d"
down_revision: str | None = "0858e875a8eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entry_profile_artifacts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("algorithm_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", name="uq_entry_profile_artifacts_entry_id"),
    )
    op.create_index(
        op.f("ix_entry_profile_artifacts_generated_at"),
        "entry_profile_artifacts",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entry_profile_artifacts_user_id"),
        "entry_profile_artifacts",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_profile_artifacts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_entry_count", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("long_term_embedding", VECTOR(1024), nullable=False),
        sa.Column("short_term_embedding", VECTOR(1024), nullable=False),
        sa.Column("algorithm_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_profile_artifacts_user_id"),
    )
    op.create_index(
        op.f("ix_user_profile_artifacts_generated_at"),
        "user_profile_artifacts",
        ["generated_at"],
        unique=False,
    )

    op.create_table(
        "restaurant_profile_artifacts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("current_timestamp(0)"),
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("restaurant_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("embedding", VECTOR(1024), nullable=False),
        sa.Column("algorithm_version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id",
            name="uq_restaurant_profile_artifacts_restaurant_id",
        ),
    )
    op.create_index(
        "ix_restaurant_profile_artifacts_embedding_hnsw",
        "restaurant_profile_artifacts",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_restaurant_profile_artifacts_generated_at"),
        "restaurant_profile_artifacts",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_restaurant_profile_artifacts_generated_at"),
        table_name="restaurant_profile_artifacts",
    )
    op.drop_index(
        "ix_restaurant_profile_artifacts_embedding_hnsw",
        table_name="restaurant_profile_artifacts",
    )
    op.drop_table("restaurant_profile_artifacts")

    op.drop_index(
        op.f("ix_user_profile_artifacts_generated_at"), table_name="user_profile_artifacts"
    )
    op.drop_table("user_profile_artifacts")

    op.drop_index(op.f("ix_entry_profile_artifacts_user_id"), table_name="entry_profile_artifacts")
    op.drop_index(
        op.f("ix_entry_profile_artifacts_generated_at"), table_name="entry_profile_artifacts"
    )
    op.drop_table("entry_profile_artifacts")
