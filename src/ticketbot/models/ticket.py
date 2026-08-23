from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column

from ticketbot.models.base import Base


class TicketStatus(StrEnum):
    """Lifecycle status of a ticket channel.

    The old SQLite layer stored these as free-form text and was inconsistent about
    casing ("Active" from the creation flow, "active" from /create); the enum
    normalizes both to the lowercase members below.
    """

    ACTIVE = "active"
    ONHOLD = "onhold"
    ARCHIVED = "archived"


class Ticket(Base):
    """One open ticket channel.

    Replaces the untyped SQLite `TicketData` table, where every column round-tripped
    as text: Discord snowflakes are now BIGINT, `created_at` is a real timestamp
    rather than a pre-formatted display string, and `claimed_by` is NULL when
    unclaimed instead of holding the literal string "No".
    """

    __tablename__ = "tickets"

    # Surrogate primary key. Every table uses one so identity is uniform and independent
    # of the business data; `channel_id` stays UNIQUE because one channel is still one
    # ticket, and the upserts in utils/database.py conflict-target that constraint.
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    claimed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda enum: [member.value for member in enum]),
        nullable=False,
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    def __repr__(self) -> str:
        return (
            f"Ticket(id={self.id}, channel_id={self.channel_id}, author_id={self.author_id}, "
            f"type={self.type!r}, status={self.status.value!r})"
        )
