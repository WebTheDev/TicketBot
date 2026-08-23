"""One-shot importer for pre-4.5 SQLite ticket databases.

Older TicketBot releases stored tickets in a local SQLite file (`tickets.db` by
default) in a table with no column types, where every value was text:

    ChannelID, AuthorID, Claimed, TimeCreated, Type, Status, MessageID

This script reads that table and inserts the rows into PostgreSQL, coercing each
value into the typed shape the ORM now expects:

  * IDs        -- text -> BIGINT
  * Claimed    -- the literal "No" -> NULL, otherwise the claimer's user ID
  * TimeCreated-- "08-17-2026, 14:03:22 UTC" -> an aware timestamp
  * Status     -- any casing ("Active"/"active") -> the lowercase enum member

Existing rows are left alone, so re-running it is safe.

Usage:
    uv run python scripts/migrate_sqlite_to_postgres.py [path/to/tickets.db]
"""

import asyncio
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert

from ticketbot.models import Ticket, TicketStatus
from ticketbot.utils.database import dispose, session_factory

DEFAULT_SQLITE_PATH = Path("tickets.db")

# The old code appended a timezone label to the formatted timestamp. It wrote
# whatever label the release happened to hardcode, while actually formatting the
# host's local time -- so these are best-effort interpretations of that label.
TIMEZONE_LABELS = {
    "UTC": UTC,
    "EST": ZoneInfo("America/New_York"),
    "EDT": ZoneInfo("America/New_York"),
    "CST": ZoneInfo("America/Chicago"),
    "PST": ZoneInfo("America/Los_Angeles"),
}


def parse_created_at(raw: str) -> datetime:
    """Turn a legacy display timestamp into an aware datetime.

    Falls back to the current time if the string cannot be understood, so one bad
    row never blocks the rest of the import.
    """
    value = (raw or "").strip()
    tzinfo = UTC
    parts = value.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].upper() in TIMEZONE_LABELS:
        tzinfo = TIMEZONE_LABELS[parts[1].upper()]
        value = parts[0].strip()
    for fmt in ("%m-%d-%Y, %H:%M:%S", "%m-%d-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=tzinfo)
        except ValueError:
            continue
    print(f"[WARN]: could not parse TimeCreated {raw!r}; using the current time instead")
    return datetime.now(UTC)


def parse_claimed(raw: str | None) -> int | None:
    """Map the legacy Claimed column onto a nullable user ID."""
    value = (raw or "").strip()
    if value == "" or value.lower() == "no":
        return None
    try:
        return int(value)
    except ValueError:
        print(f"[WARN]: unrecognized Claimed value {raw!r}; treating the ticket as unclaimed")
        return None


def parse_status(raw: str | None) -> TicketStatus:
    value = (raw or "").strip().lower()
    try:
        return TicketStatus(value)
    except ValueError:
        print(f"[WARN]: unrecognized Status {raw!r}; defaulting to {TicketStatus.ACTIVE.value}")
        return TicketStatus.ACTIVE


def read_legacy_rows(sqlite_path: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(sqlite_path)
    try:
        cursor = connection.execute(
            "SELECT ChannelID, AuthorID, Claimed, TimeCreated, Type, Status, MessageID "
            "FROM TicketData ORDER BY ChannelID"
        )
        rows = cursor.fetchall()
    finally:
        connection.close()

    tickets: list[dict[str, object]] = []
    for channel_id, author_id, claimed, time_created, ticket_type, status, message_id in rows:
        tickets.append(
            {
                "channel_id": int(channel_id),
                "author_id": int(author_id),
                "claimed_by": parse_claimed(claimed),
                "created_at": parse_created_at(time_created),
                "type": str(ticket_type),
                "status": parse_status(status),
                "message_id": int(message_id),
            }
        )
    return tickets


async def import_tickets(sqlite_path: Path) -> None:
    tickets = read_legacy_rows(sqlite_path)
    if not tickets:
        print(f"[MESSAGE]: No rows found in {sqlite_path}, nothing to import.")
        return

    async with session_factory() as session:
        result = await session.execute(
            insert(Ticket).values(tickets).on_conflict_do_nothing(index_elements=["channel_id"])
        )
        await session.commit()

    skipped = len(tickets) - result.rowcount
    print(f"[MESSAGE]: Imported {result.rowcount} ticket(s) from {sqlite_path}.")
    if skipped > 0:
        print(f"[MESSAGE]: Skipped {skipped} ticket(s) already present in PostgreSQL.")


def main() -> None:
    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SQLITE_PATH
    if not sqlite_path.exists():
        print(f"[ERROR]: No SQLite database at {sqlite_path}.")
        print("[ERROR]: Pass the path explicitly, e.g. uv run python scripts/migrate_sqlite_to_postgres.py ./tickets.db")
        raise SystemExit(1)

    async def run() -> None:
        try:
            await import_tickets(sqlite_path)
        finally:
            await dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
