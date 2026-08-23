from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ticketbot.models.base import Base

# Discord caps a select menu at 25 options and each option's label, value, and
# description at 100 characters. Ticket types render as select options, so these are
# hard limits on what may be stored -- see functions/config_commands.py for enforcement.
MAX_TICKET_TYPES = 25
MAX_SELECT_FIELD_LENGTH = 100


class TicketType(Base):
    """One selectable ticket type, replacing the old `options_dict` setting.

    `key` is the value shared with `Ticket.type` and with the per-type role rows; it is
    what the old config called the "Type of Option". `position` controls the order the
    types appear in the creation dropdown.
    """

    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    roles: Mapped[list["TicketTypeRole"]] = relationship(
        back_populates="ticket_type", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"TicketType(key={self.key!r}, label={self.label!r}, position={self.position})"


class TicketTypeRole(Base):
    """A role granted access to one ticket type, replacing `channel_perms`.

    The old config kept ticket types and their roles in two separate dicts that had to
    be edited in lockstep; mismatched keys silently produced tickets with no staff
    access. The foreign key here makes that mismatch impossible.
    """

    __tablename__ = "ticket_type_roles"
    __table_args__ = (UniqueConstraint("type_key", "role_id", name="uq_ticket_type_roles_type_role"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Still references ticket_types.key rather than its new id: the key is UNIQUE, the
    # cache and the /config commands both address types by key, and pointing the FK at
    # the id would force a join on a hot cached read path for no gain.
    type_key: Mapped[str] = mapped_column(
        Text, ForeignKey("ticket_types.key", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    ticket_type: Mapped[TicketType] = relationship(back_populates="roles")

    def __repr__(self) -> str:
        return f"TicketTypeRole(type_key={self.type_key!r}, role_id={self.role_id})"


class BotSetting(Base):
    """A single live-editable scalar setting.

    Values are JSONB so ints, bools, and strings round-trip without the caller having
    to know which is which. Keys are the same names the pydantic Settings class uses
    (e.g. "embed_color"), so the runtime overlay can resolve them by attribute name.
    """

    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"BotSetting(key={self.key!r}, value={self.value!r})"
