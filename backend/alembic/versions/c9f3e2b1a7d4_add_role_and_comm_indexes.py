"""add role and communication indexes

Revision ID: c9f3e2b1a7d4
Revises: 795b8433c0bc
Create Date: 2026-03-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9f3e2b1a7d4"
down_revision: Union[str, None] = "795b8433c0bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _has_unique_constraint(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(c["name"] == constraint_name for c in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "users", "role"):
        op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="user"))

    # Keep defaults explicit in existing rows and remove server_default afterwards.
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", server_default=None)

    if not _has_index(inspector, "users", "ix_users_role"):
        op.create_index("ix_users_role", "users", ["role"], unique=False)

    if not _has_unique_constraint(inspector, "conversations", "uix_conversation_listing_participants"):
        op.create_unique_constraint(
            "uix_conversation_listing_participants",
            "conversations",
            ["listing_id", "participant_a_id", "participant_b_id"],
        )

    if not _has_index(inspector, "messages", "ix_messages_sent_at"):
        op.create_index("ix_messages_sent_at", "messages", ["sent_at"], unique=False)

    if not _has_index(inspector, "notifications", "ix_notifications_created_at"):
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)

    if not _has_index(inspector, "reports", "ix_reports_target_type_target_id"):
        op.create_index("ix_reports_target_type_target_id", "reports", ["target_type", "target_id"], unique=False)

    if not _has_index(inspector, "reports", "ix_reports_status"):
        op.create_index("ix_reports_status", "reports", ["status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "reports", "ix_reports_status"):
        op.drop_index("ix_reports_status", table_name="reports")
    if _has_index(inspector, "reports", "ix_reports_target_type_target_id"):
        op.drop_index("ix_reports_target_type_target_id", table_name="reports")
    if _has_index(inspector, "notifications", "ix_notifications_created_at"):
        op.drop_index("ix_notifications_created_at", table_name="notifications")
    if _has_index(inspector, "messages", "ix_messages_sent_at"):
        op.drop_index("ix_messages_sent_at", table_name="messages")

    if _has_unique_constraint(inspector, "conversations", "uix_conversation_listing_participants"):
        op.drop_constraint("uix_conversation_listing_participants", "conversations", type_="unique")

    if _has_index(inspector, "users", "ix_users_role"):
        op.drop_index("ix_users_role", table_name="users")

    if _has_column(inspector, "users", "role"):
        op.drop_column("users", "role")
