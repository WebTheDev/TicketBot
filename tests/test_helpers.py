"""Tests for the shared formatting and presence helpers."""

from datetime import UTC, datetime, timedelta, timezone

import discord
import pytest

from ticketbot.utils.database import DatabaseHealth
from ticketbot.utils.helpers import (
    CREATION_EMBED_TITLE,
    apply_presence,
    build_creation_embed,
    format_created_at,
    is_creation_embed,
    overall_status,
    resolve_activity_type,
)


class TestFormatCreatedAt:
    def test_renders_the_legacy_display_shape(self):
        created_at = datetime(2026, 8, 17, 14, 3, 22, tzinfo=UTC)
        assert format_created_at(created_at) == "08-17-2026, 14:03:22 UTC"

    def test_converts_other_timezones_to_utc(self):
        eastern = datetime(2026, 8, 17, 10, 3, 22, tzinfo=timezone(timedelta(hours=-4)))
        assert format_created_at(eastern) == "08-17-2026, 14:03:22 UTC"


class TestResolveActivityType:
    @pytest.mark.parametrize(
        ("configured", "expected"),
        [
            ("Playing", discord.ActivityType.playing),
            ("streaming", discord.ActivityType.streaming),
            ("WATCHING", discord.ActivityType.watching),
            ("Listening", discord.ActivityType.listening),
        ],
    )
    def test_recognizes_each_type_regardless_of_casing(self, configured, expected):
        activity_type, recognized = resolve_activity_type(configured)
        assert activity_type == expected
        assert recognized is True

    @pytest.mark.parametrize("configured", ["", None, "Vibing"])
    def test_falls_back_to_playing_and_reports_it(self, configured):
        activity_type, recognized = resolve_activity_type(configured)
        assert activity_type == discord.ActivityType.playing
        assert recognized is False


class FakeBot:
    def __init__(self):
        self.presence = None

    async def change_presence(self, *, status, activity):
        self.presence = (status, activity)


class TestApplyPresence:
    async def test_pushes_the_configured_activity(self):
        bot = FakeBot()
        recognized = await apply_presence(bot, "Watching", "the tickets")

        status, activity = bot.presence
        assert recognized is True
        assert status == discord.Status.online
        assert activity.type == discord.ActivityType.watching
        assert activity.name == "the tickets"

    async def test_still_sets_presence_for_an_unknown_type(self):
        bot = FakeBot()
        recognized = await apply_presence(bot, "Vibing", "anyway")

        _, activity = bot.presence
        assert recognized is False
        assert activity.type == discord.ActivityType.playing
        assert activity.name == "anyway"

    async def test_handles_an_empty_status_message(self):
        bot = FakeBot()
        await apply_presence(bot, "Playing", None)

        _, activity = bot.presence
        assert activity.name == ""


class TestDatabaseHealthDescribe:
    def test_reports_a_reachable_database_with_its_round_trip(self):
        assert DatabaseHealth(reachable=True, latency_ms=12.4).describe() == "✅ Connected (12ms)"

    def test_reports_why_an_unreachable_database_failed(self):
        described = DatabaseHealth(reachable=False, error="OperationalError").describe()
        assert "Unreachable" in described
        assert "OperationalError" in described


class TestOverallStatus:
    def test_is_only_good_when_the_database_answers(self):
        healthy = DatabaseHealth(reachable=True, latency_ms=8.0)
        assert overall_status(healthy, gateway_latency_ms=42.0) == "Everything is good ✅"

    def test_reports_degraded_when_the_database_is_down(self):
        down = DatabaseHealth(reachable=False, error="OperationalError")
        assert "Degraded" in overall_status(down, gateway_latency_ms=42.0)

    def test_flags_a_slow_gateway(self):
        healthy = DatabaseHealth(reachable=True, latency_ms=8.0)
        described = overall_status(healthy, gateway_latency_ms=900.0)
        assert "Slow" in described
        assert "900ms" in described

    def test_an_unreachable_database_outranks_a_slow_gateway(self):
        down = DatabaseHealth(reachable=False, error="OperationalError")
        assert "Degraded" in overall_status(down, gateway_latency_ms=900.0)


class _User:
    def __init__(self, user_id):
        self.id = user_id
        self.display_avatar = "https://example.invalid/avatar.png"
        self.name = "TicketBot"


class _BotUser:
    def __init__(self, user_id=999):
        self.user = _User(user_id)


class _Message:
    def __init__(self, author_id, embeds):
        self.author = _User(author_id)
        self.embeds = embeds


class TestCreationEmbedIdentification:
    """Startup adopts an existing embed by recognizing it, so these must agree."""

    def test_a_freshly_built_embed_is_recognized(self):
        bot = _BotUser(999)
        embed = build_creation_embed(bot, 0x5865F2, "My Server")
        assert is_creation_embed(_Message(999, [embed]), 999) is True

    def test_the_title_is_the_shared_marker(self):
        embed = build_creation_embed(_BotUser(), 0x5865F2, "My Server")
        assert embed.title == CREATION_EMBED_TITLE

    def test_appearance_settings_are_applied(self):
        embed = build_creation_embed(_BotUser(42), 0x5865F2, "My Server")
        assert embed.color.value == 0x5865F2
        assert embed.footer.text == "My Server | 42"

    def test_another_bots_creation_embed_is_not_adopted(self):
        # Adopting a different bot's message would mean editing something we cannot edit.
        embed = build_creation_embed(_BotUser(111), 0x5865F2, "Theirs")
        assert is_creation_embed(_Message(111, [embed]), 999) is False

    def test_an_unrelated_message_is_not_adopted(self):
        other = discord.Embed(title="**Server Rules**", description="Be nice.")
        assert is_creation_embed(_Message(999, [other]), 999) is False

    def test_a_plain_message_is_not_adopted(self):
        assert is_creation_embed(_Message(999, []), 999) is False
