from datetime import UTC, datetime
from importlib.metadata import version
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:  # importing utils.database eagerly would build the engine just to read a flag
    from ticketbot.utils.database import DatabaseHealth

# Gateway round trips above this are worth flagging in /info even though nothing is
# actually broken -- it is usually the first visible sign of a struggling host.
SLOW_GATEWAY_LATENCY_MS = 500.0

# Maps the bot_status_type setting onto discord's activity types. Anything unrecognized
# falls back to "playing", which is what the original startup code did.
ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "streaming": discord.ActivityType.streaming,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
}


# The title identifies the creation embed on startup, when the bot searches its channel
# for a message it posted previously rather than posting a duplicate.
CREATION_EMBED_TITLE = "**Create a ticket**"


def build_creation_embed(bot: discord.Client, color: int, footer: str | None) -> discord.Embed:
    """The "Create a ticket" embed, built from the live appearance settings."""
    embed = discord.Embed(
        title=CREATION_EMBED_TITLE,
        description="Press the button below to create a ticket!",
        color=color,
    )
    embed.set_footer(text=f"{footer} | {bot.user.id}", icon_url=f"{bot.user.display_avatar}")
    return embed


def is_creation_embed(message: discord.Message, bot_user_id: int) -> bool:
    """Whether `message` is a creation embed this bot posted."""
    if message.author.id != bot_user_id or not message.embeds:
        return False
    return message.embeds[0].title == CREATION_EMBED_TITLE


def resolve_activity_type(status_type: str | None) -> tuple[discord.ActivityType, bool]:
    """Return the activity type for a configured status, and whether it was recognized."""
    key = (status_type or "").strip().lower()
    if key in ACTIVITY_TYPES:
        return ACTIVITY_TYPES[key], True
    return discord.ActivityType.playing, False


async def apply_presence(bot: discord.Client, status_type: str | None, message: str | None) -> bool:
    """Push the configured presence to Discord.

    Shared by startup and by `/config set`, so changing the status settings takes effect
    immediately instead of waiting for a restart. Returns whether the status type was
    recognized, letting the caller warn about a typo.
    """
    activity_type, recognized = resolve_activity_type(status_type)
    activity = discord.Activity(type=activity_type, name=f"{message or ''}")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    return recognized


def format_created_at(created_at: datetime) -> str:
    """Render a ticket's creation time the way the old text column read.

    Ticket timestamps are stored as real timestamptz values now, but embeds should
    still show the "08-17-2026, 14:03:22 UTC" shape members are used to seeing.
    """
    return created_at.astimezone(UTC).strftime("%m-%d-%Y, %H:%M:%S UTC")


def get_project_version() -> str:
    return version("ticketbot")


def overall_status(database: "DatabaseHealth", gateway_latency_ms: float) -> str:
    """Summarise the bot's health for the /info embed.

    This replaces a hardcoded "Everything is good", so it is only allowed to say that
    when the checks it is given actually passed.
    """
    if not database.reachable:
        return "\u274c Degraded \u2014 the database is unreachable"
    if gateway_latency_ms > SLOW_GATEWAY_LATENCY_MS:
        return f"\u26a0\ufe0f Slow \u2014 gateway latency is {gateway_latency_ms:.0f}ms"
    return "Everything is good \u2705"
