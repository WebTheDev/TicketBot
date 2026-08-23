"""Tests for the legacy SQLite importer's coercion of untyped text values."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ticketbot.models import TicketStatus
from scripts.migrate_sqlite_to_postgres import (
    parse_claimed,
    parse_created_at,
    parse_status,
    read_legacy_rows,
)


class TestParseClaimed:
    @pytest.mark.parametrize("raw", ["No", "no", "NO", "", "   ", None])
    def test_unclaimed_sentinels_become_none(self, raw):
        assert parse_claimed(raw) is None

    def test_a_user_id_is_kept(self):
        assert parse_claimed("123456789012345678") == 123456789012345678

    def test_unparseable_values_degrade_to_unclaimed(self):
        assert parse_claimed("somebody") is None


class TestParseStatus:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Active", TicketStatus.ACTIVE),
            ("active", TicketStatus.ACTIVE),
            ("Onhold", TicketStatus.ONHOLD),
            ("ARCHIVED", TicketStatus.ARCHIVED),
        ],
    )
    def test_normalizes_casing(self, raw, expected):
        # Old installs held both "Active" (creation flow) and "active" (/create).
        assert parse_status(raw) == expected

    def test_unknown_status_defaults_to_active(self):
        assert parse_status("weird") == TicketStatus.ACTIVE


class TestParseCreatedAt:
    def test_parses_a_utc_labelled_timestamp(self):
        assert parse_created_at("08-17-2026, 14:03:22 UTC") == datetime(
            2026, 8, 17, 14, 3, 22, tzinfo=UTC
        )

    def test_an_eastern_label_is_converted_to_the_right_instant(self):
        parsed = parse_created_at("08-16-2026, 09:15:00 EST")
        assert parsed.astimezone(UTC) == datetime(2026, 8, 16, 13, 15, tzinfo=UTC)

    def test_an_unlabelled_timestamp_is_assumed_utc(self):
        assert parse_created_at("08-17-2026, 14:03:22").tzinfo == UTC

    def test_unparseable_input_falls_back_to_now_rather_than_raising(self):
        # One malformed row must not block the rest of the import.
        parsed = parse_created_at("nonsense")
        assert (datetime.now(UTC) - parsed).total_seconds() < 10


class TestReadLegacyRows:
    @pytest.fixture
    def legacy_db(self, tmp_path: Path) -> Path:
        path = tmp_path / "tickets.db"
        connection = sqlite3.connect(path)
        connection.execute(
            "CREATE TABLE TicketData(ChannelID, AuthorID, Claimed, TimeCreated, Type, Status, MessageID)"
        )
        connection.executemany(
            "INSERT INTO TicketData VALUES (?,?,?,?,?,?,?)",
            [
                ("111", "222", "No", "08-17-2026, 14:03:22 UTC", "support", "Active", "333"),
                ("444", "555", "666", "08-16-2026, 09:15:00 UTC", "sales", "onhold", "777"),
            ],
        )
        connection.commit()
        connection.close()
        return path

    def test_converts_every_column_to_its_typed_form(self, legacy_db):
        rows = read_legacy_rows(legacy_db)

        assert rows == [
            {
                "channel_id": 111,
                "author_id": 222,
                "claimed_by": None,
                "created_at": datetime(2026, 8, 17, 14, 3, 22, tzinfo=UTC),
                "type": "support",
                "status": TicketStatus.ACTIVE,
                "message_id": 333,
            },
            {
                "channel_id": 444,
                "author_id": 555,
                "claimed_by": 666,
                "created_at": datetime(2026, 8, 16, 9, 15, tzinfo=UTC),
                "type": "sales",
                "status": TicketStatus.ONHOLD,
                "message_id": 777,
            },
        ]

    def test_rows_come_back_ordered_by_channel(self, legacy_db):
        rows = read_legacy_rows(legacy_db)
        assert [row["channel_id"] for row in rows] == sorted(row["channel_id"] for row in rows)
