"""add payment and promotion fields

Revision ID: e1a2c3d4f5a6
Revises: c9f3e2b1a7d4
Create Date: 2026-03-27 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1a2c3d4f5a6"
down_revision: Union[str, None] = "c9f3e2b1a7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_fk(inspector: sa.Inspector, table_name: str, fk_name: str) -> bool:
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "promotion_packages", "currency"):
        op.add_column(
            "promotion_packages",
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="KGS"),
        )
        with op.batch_alter_table("promotion_packages") as batch_op:
            batch_op.alter_column("currency", server_default=None)

    if not _has_column(inspector, "payments", "promotion_package_id"):
        op.add_column("payments", sa.Column("promotion_package_id", sa.Integer(), nullable=True))

    if not _has_fk(inspector, "payments", "fk_payments_promotion_package_id"):
        op.create_foreign_key(
            "fk_payments_promotion_package_id",
            "payments",
            "promotion_packages",
            ["promotion_package_id"],
            ["id"],
        )

    if not _has_column(inspector, "payments", "expires_at"):
        op.add_column("payments", sa.Column("expires_at", sa.DateTime(), nullable=True))

    if not _has_column(inspector, "promotions", "promotion_package_id"):
        op.add_column("promotions", sa.Column("promotion_package_id", sa.Integer(), nullable=True))

    if not _has_fk(inspector, "promotions", "fk_promotions_promotion_package_id"):
        op.create_foreign_key(
            "fk_promotions_promotion_package_id",
            "promotions",
            "promotion_packages",
            ["promotion_package_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_fk(inspector, "promotions", "fk_promotions_promotion_package_id"):
        op.drop_constraint("fk_promotions_promotion_package_id", "promotions", type_="foreignkey")

    if _has_column(inspector, "promotions", "promotion_package_id"):
        op.drop_column("promotions", "promotion_package_id")

    if _has_column(inspector, "payments", "expires_at"):
        op.drop_column("payments", "expires_at")

    if _has_fk(inspector, "payments", "fk_payments_promotion_package_id"):
        op.drop_constraint("fk_payments_promotion_package_id", "payments", type_="foreignkey")

    if _has_column(inspector, "payments", "promotion_package_id"):
        op.drop_column("payments", "promotion_package_id")

    if _has_column(inspector, "promotion_packages", "currency"):
        op.drop_column("promotion_packages", "currency")
