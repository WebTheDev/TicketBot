"""initial schema

Revision ID: d4e2930d2ec9
Revises: 
Create Date: 2026-08-22 15:26:43.020393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e2930d2ec9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The complete TicketBot schema as a single baseline revision.
#
# Two conventions run through it:
#   * Every table is keyed on a surrogate BIGINT identity column. The natural keys the
#     tables are addressed by stay UNIQUE -- the application looks rows up by them, and
#     the ON CONFLICT upserts in utils/database.py need a unique index as their conflict
#     target -- but they are no longer the primary key.
#   * The ticket_status enum is created and dropped explicitly. Declaring the column with
#     create_type=False stops create_table from emitting a second CREATE TYPE.

ticket_status = postgresql.ENUM(
    "active", "onhold", "archived", name="ticket_status", create_type=False
)


def upgrade() -> None:
    """Upgrade schema."""
    ticket_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        # One channel is exactly one ticket, so channel_id keeps a UNIQUE constraint;
        # TicketRepository.find() and the SQLite importer's upsert both rely on it.
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("claimed_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="uq_tickets_channel_id"),
    )
    op.create_index(op.f("ix_tickets_author_id"), "tickets", ["author_id"], unique=False)

    op.create_table(
        "ticket_types",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_ticket_types_key"),
    )

    op.create_table(
        "ticket_type_roles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        # The foreign key targets ticket_types.key rather than its surrogate id: the key
        # is UNIQUE, and both the runtime cache and the /config commands address ticket
        # types by key, so pointing at the id would only add a join.
        sa.Column("type_key", sa.Text(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["type_key"], ["ticket_types.key"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type_key", "role_id", name="uq_ticket_type_roles_type_role"),
    )

    op.create_table(
        "bot_settings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_bot_settings_key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("bot_settings")
    op.drop_table("ticket_type_roles")
    op.drop_table("ticket_types")
    op.drop_index(op.f("ix_tickets_author_id"), table_name="tickets")
    op.drop_table("tickets")
    ticket_status.drop(op.get_bind(), checkfirst=True)
