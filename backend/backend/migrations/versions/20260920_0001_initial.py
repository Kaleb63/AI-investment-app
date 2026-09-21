"""Create users, Plaid items, watchlists, saved screens, and history tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "analysis_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("ticker", sa.String(length=15), nullable=False),
        sa.Column("metrics_snapshot", sa.JSON(), nullable=False),
        sa.Column("score_snapshot", sa.JSON(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_history_created_at"),
        "analysis_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_history_ticker"),
        "analysis_history",
        ["ticker"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_history_user_id"),
        "analysis_history",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "plaid_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plaid_item_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("institution_id", sa.String(length=255), nullable=True),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("account_metadata", sa.JSON(), nullable=False),
        sa.Column("connection_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plaid_items_plaid_item_id"),
        "plaid_items",
        ["plaid_item_id"],
        unique=True,
    )
    op.create_index(op.f("ix_plaid_items_user_id"), "plaid_items", ["user_id"], unique=False)

    op.create_table(
        "saved_screens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_saved_screens_user_id"),
        "saved_screens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "scan_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("stocks_analyzed", sa.Integer(), nullable=False),
        sa.Column("matches", sa.Integer(), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_history_created_at"),
        "scan_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_history_user_id"),
        "scan_history",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "watchlist_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("ticker", sa.String(length=15), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),
    )
    op.create_index(
        op.f("ix_watchlist_entries_ticker"),
        "watchlist_entries",
        ["ticker"],
        unique=False,
    )
    op.create_index(
        op.f("ix_watchlist_entries_user_id"),
        "watchlist_entries",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("watchlist_entries")
    op.drop_table("scan_history")
    op.drop_table("saved_screens")
    op.drop_table("plaid_items")
    op.drop_table("analysis_history")
    op.drop_table("users")
