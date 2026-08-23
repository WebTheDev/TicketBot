import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ticketbot.config import settings
from ticketbot.models import BotSetting, Ticket, TicketStatus, TicketType, TicketTypeRole

# create_async_engine is lazy -- no connection is opened until the first query, so
# building the engine at import time is safe even though the event loop isn't running yet.
engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def dispose() -> None:
    """Close the connection pool. Call once during bot shutdown."""
    await engine.dispose()


async def schema_ready() -> bool:
    """Report whether the tickets table exists and is reachable.

    Replaces the old verifylayout/createlayout pair: Alembic owns DDL now, so a
    missing table means migrations have not been run rather than a first launch.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM tickets LIMIT 1"))
            await connection.execute(text("SELECT 1 FROM ticket_types LIMIT 1"))
            await connection.execute(text("SELECT 1 FROM bot_settings LIMIT 1"))
    except SQLAlchemyError:
        return False
    return True


# How long a health probe is allowed to take before it is reported as unreachable.
# /info has to answer inside Discord's interaction window, so a hung database must
# fail fast rather than stall the command.
HEALTH_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class DatabaseHealth:
    """The result of one live probe against the configured PostgreSQL server."""

    reachable: bool
    latency_ms: float | None = None
    error: str | None = None

    def describe(self) -> str:
        """Render the probe for an embed field."""
        if self.reachable:
            return f"\u2705 Connected ({self.latency_ms:.0f}ms)"
        return f"\u274c Unreachable ({self.error})"


async def health() -> DatabaseHealth:
    """Measure a real round trip to the database.

    /info used to claim "Everything is good" unconditionally, which was a lie the
    moment PostgreSQL went away. This opens a connection and runs a trivial query so
    the reported status reflects the database as it is right now, including the pool
    having to dial out when the bot has been idle.
    """
    started = time.perf_counter()
    try:
        async with asyncio.timeout(HEALTH_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except TimeoutError:
        return DatabaseHealth(reachable=False, error=f"timed out after {HEALTH_TIMEOUT_SECONDS:.0f}s")
    except (SQLAlchemyError, OSError) as error:
        # asyncpg raises bare OSErrors for DNS/refused-connection failures, which
        # SQLAlchemy does not always wrap, so both families are caught here.
        return DatabaseHealth(reachable=False, error=type(error).__name__)
    return DatabaseHealth(reachable=True, latency_ms=(time.perf_counter() - started) * 1000)


class TicketRepository:
    """Async data access for `Ticket` rows.

    Every method opens its own short-lived session, mirroring the connect/close
    pattern the call sites already used -- just without blocking the event loop.
    """

    @staticmethod
    async def add(
        channel_id: int,
        author_id: int,
        created_at: datetime,
        type: str,
        status: TicketStatus,
        message_id: int,
    ) -> Ticket:
        ticket = Ticket(
            channel_id=channel_id,
            author_id=author_id,
            claimed_by=None,
            created_at=created_at,
            type=type,
            status=status,
            message_id=message_id,
        )
        async with session_factory() as session:
            session.add(ticket)
            await session.commit()
        return ticket

    @staticmethod
    async def find(channel_id: int) -> Ticket | None:
        """Look up one ticket by its channel ID.

        `channel_id` is no longer the primary key -- tables carry a surrogate `id` now --
        so this is an explicit query against its UNIQUE index rather than session.get().
        """
        async with session_factory() as session:
            return await session.scalar(select(Ticket).where(Ticket.channel_id == channel_id))

    @staticmethod
    async def all_tickets() -> list[Ticket]:
        async with session_factory() as session:
            result = await session.scalars(select(Ticket).order_by(Ticket.channel_id))
            return list(result)

    @staticmethod
    async def find_open_ticket_for(author_id: int, exclude_type: str) -> Ticket | None:
        """Find an author's first non-archived ticket, ignoring one ticket type.

        Backs the "one ticket at a time" rule. The type exclusion lets staff-only
        ticket types sit outside the limit.
        """
        async with session_factory() as session:
            return await session.scalar(
                select(Ticket)
                .where(
                    Ticket.author_id == author_id,
                    Ticket.status != TicketStatus.ARCHIVED,
                    Ticket.type != exclude_type,
                )
                .order_by(Ticket.channel_id)
                .limit(1)
            )

    @staticmethod
    async def set_claimed(channel_id: int, user_id: int) -> None:
        async with session_factory() as session:
            await session.execute(
                update(Ticket).where(Ticket.channel_id == channel_id).values(claimed_by=user_id)
            )
            await session.commit()

    @staticmethod
    async def set_status(channel_id: int, status: TicketStatus) -> None:
        async with session_factory() as session:
            await session.execute(
                update(Ticket).where(Ticket.channel_id == channel_id).values(status=status)
            )
            await session.commit()

    @staticmethod
    async def count_by_type(type_key: str) -> int:
        """Count tickets of one type. Backs the guard against deleting a type in use."""
        async with session_factory() as session:
            return await session.scalar(
                select(func.count()).select_from(Ticket).where(Ticket.type == type_key)
            )

    @staticmethod
    async def delete(channel_id: int) -> None:
        async with session_factory() as session:
            await session.execute(sql_delete(Ticket).where(Ticket.channel_id == channel_id))
            await session.commit()


class ConfigRepository:
    """Async data access for the live-editable configuration tables.

    Reads here are expected to be infrequent -- `utils.runtime_config` caches the
    results and only reloads on startup and after a write.
    """

    @staticmethod
    async def all_types() -> list[TicketType]:
        async with session_factory() as session:
            result = await session.scalars(
                select(TicketType).order_by(TicketType.position, TicketType.key)
            )
            return list(result)

    @staticmethod
    async def find_type(key: str) -> TicketType | None:
        async with session_factory() as session:
            return await session.scalar(select(TicketType).where(TicketType.key == key))

    @staticmethod
    async def upsert_type(key: str, label: str, description: str, position: int) -> None:
        async with session_factory() as session:
            await session.execute(
                pg_insert(TicketType)
                .values(key=key, label=label, description=description, position=position)
                .on_conflict_do_update(
                    index_elements=["key"],
                    set_={"label": label, "description": description, "position": position},
                )
            )
            await session.commit()

    @staticmethod
    async def delete_type(key: str) -> None:
        """Delete a type. Its role rows go with it via ON DELETE CASCADE."""
        async with session_factory() as session:
            await session.execute(sql_delete(TicketType).where(TicketType.key == key))
            await session.commit()

    @staticmethod
    async def all_roles() -> list[TicketTypeRole]:
        async with session_factory() as session:
            result = await session.scalars(select(TicketTypeRole))
            return list(result)

    @staticmethod
    async def add_role(type_key: str, role_id: int) -> None:
        async with session_factory() as session:
            await session.execute(
                pg_insert(TicketTypeRole)
                .values(type_key=type_key, role_id=role_id)
                .on_conflict_do_nothing(index_elements=["type_key", "role_id"])
            )
            await session.commit()

    @staticmethod
    async def remove_role(type_key: str, role_id: int) -> bool:
        """Remove one role from a type. Returns whether a row was actually removed."""
        async with session_factory() as session:
            result = await session.execute(
                sql_delete(TicketTypeRole).where(
                    TicketTypeRole.type_key == type_key,
                    TicketTypeRole.role_id == role_id,
                )
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def all_settings() -> dict[str, Any]:
        async with session_factory() as session:
            result = await session.scalars(select(BotSetting))
            return {row.key: row.value for row in result}

    @staticmethod
    async def set_setting(key: str, value: Any) -> None:
        async with session_factory() as session:
            await session.execute(
                pg_insert(BotSetting)
                .values(key=key, value=value)
                .on_conflict_do_update(index_elements=["key"], set_={"value": value})
            )
            await session.commit()

    @staticmethod
    async def seed(types: list[dict[str, Any]], roles: list[dict[str, Any]], scalars: dict[str, Any]) -> None:
        """Populate empty config tables in one transaction.

        Used once per install to carry `.env` values over. Existing rows are left
        alone, so a partially seeded database will not be clobbered.
        """
        async with session_factory() as session:
            if types:
                await session.execute(
                    pg_insert(TicketType).values(types).on_conflict_do_nothing(index_elements=["key"])
                )
            if roles:
                await session.execute(
                    pg_insert(TicketTypeRole)
                    .values(roles)
                    .on_conflict_do_nothing(index_elements=["type_key", "role_id"])
                )
            if scalars:
                await session.execute(
                    pg_insert(BotSetting)
                    .values([{"key": key, "value": value} for key, value in scalars.items()])
                    .on_conflict_do_nothing(index_elements=["key"])
                )
            await session.commit()
