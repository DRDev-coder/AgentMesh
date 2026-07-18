"""Replace Stripe-specific billing storage with Razorpay fields.

Revision ID: 0002_razorpay_billing
Revises: 0001_multitenant_foundation
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0002_razorpay_billing"
down_revision = "0001_multitenant_foundation"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _rename_column(table: str, old: str, new: str) -> None:
    columns = _columns(table)
    if old in columns and new not in columns:
        op.alter_column(table, old, new_column_name=new)


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    _rename_column("organizations", "spend_cap_cents", "spend_cap_paise")
    _rename_column("usage_events", "stripe_status", "razorpay_status")
    _rename_column("usage_events", "stripe_event_id", "razorpay_addon_id")
    _rename_column("billing_accounts", "stripe_customer_id", "razorpay_customer_id")
    _rename_column(
        "billing_accounts", "stripe_subscription_id", "razorpay_subscription_id"
    )
    if "razorpay_subscription_url" not in _columns("billing_accounts"):
        op.add_column(
            "billing_accounts",
            sa.Column("razorpay_subscription_url", sa.String(length=500), nullable=True),
        )
    if "stripe_events" in tables and "razorpay_events" not in tables:
        op.rename_table("stripe_events", "razorpay_events")


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "razorpay_events" in tables and "stripe_events" not in tables:
        op.rename_table("razorpay_events", "stripe_events")
    columns = _columns("billing_accounts")
    if "razorpay_subscription_url" in columns:
        op.drop_column("billing_accounts", "razorpay_subscription_url")
    _rename_column(
        "billing_accounts", "razorpay_subscription_id", "stripe_subscription_id"
    )
    _rename_column("billing_accounts", "razorpay_customer_id", "stripe_customer_id")
    _rename_column("usage_events", "razorpay_addon_id", "stripe_event_id")
    _rename_column("usage_events", "razorpay_status", "stripe_status")
    _rename_column("organizations", "spend_cap_paise", "spend_cap_cents")
