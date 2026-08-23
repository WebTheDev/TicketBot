"""Validation and coercion for live config edits.

These are deliberately pure functions with no Discord or database dependencies: the
rules they encode are the ways a live config edit can break the bot at runtime, so they
are the part most worth testing directly.
"""

import re
from dataclasses import dataclass
from typing import Any

from ticketbot.models import MAX_SELECT_FIELD_LENGTH, MAX_TICKET_TYPES


@dataclass(frozen=True)
class SettingSpec:
    """One live-editable setting, and everything needed to show it to a human."""

    key: str
    kind: str
    label: str
    group: str
    help: str
    example: str


SETTING_SPECS: tuple[SettingSpec, ...] = (
    SettingSpec(
        key="embed_color",
        kind="color",
        label="Embed Color",
        group="Appearance",
        help="The accent color down the side of every embed I send.",
        example="#5865F2",
    ),
    SettingSpec(
        key="footer_of_embeds",
        kind="str",
        label="Embed Footer",
        group="Appearance",
        help="The text I show in the footer of every embed, before my ID.",
        example="My Server Support",
    ),
    SettingSpec(
        key="bot_status_type",
        kind="status_type",
        label="Status Type",
        group="Presence",
        help=f"How my status reads: {', '.join(('Playing', 'Streaming', 'Watching', 'Listening'))}.",
        example="Watching",
    ),
    SettingSpec(
        key="bot_status_message",
        kind="str",
        label="Status Message",
        group="Presence",
        help="The text after my status type, e.g. Watching *for new tickets*.",
        example="for new tickets",
    ),
    SettingSpec(
        key="multiple_tickets_allowed",
        kind="bool",
        label="Multiple Tickets Per Member",
        group="Tickets",
        help="Whether I let a member have more than one ticket open at a time.",
        example="false",
    ),
    SettingSpec(
        key="dm_ticket_copies",
        kind="bool",
        label="DM Transcript Copies",
        group="Tickets",
        help="Whether I DM the ticket author a copy of the transcript when a ticket closes.",
        example="true",
    ),
    SettingSpec(
        key="auto_post_creation_embed",
        kind="bool",
        label="Auto-Post Creation Embed",
        group="Tickets",
        help=(
            "Whether I post a new ticket creation embed at startup when I don't have one on "
            "record. Turn this off if you'd rather point me at an existing message with "
            "`/ticket config creation-message`."
        ),
        example="true",
    ),
    SettingSpec(
        key="ticket_type_allowed_to_create_private_channels",
        kind="str",
        label="Private Ticket Type",
        group="Tickets",
        help="The ticket type whose staff roles may ask me to open private tickets with `/ticket create`.",
        example="staff",
    ),
)

SPECS_BY_KEY: dict[str, SettingSpec] = {spec.key: spec for spec in SETTING_SPECS}

SETTABLE: dict[str, str] = {spec.key: spec.kind for spec in SETTING_SPECS}

SETTING_GROUPS: tuple[str, ...] = tuple(dict.fromkeys(spec.group for spec in SETTING_SPECS))

STATUS_TYPES = ("Playing", "Streaming", "Watching", "Listening")

TRUE_WORDS = {"true", "yes", "on", "1", "enable", "enabled"}
FALSE_WORDS = {"false", "no", "off", "0", "disable", "disabled"}


class ConfigValidationError(ValueError):
    """Raised when a proposed config value would be invalid or unusable."""


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in TRUE_WORDS:
        return True
    if value in FALSE_WORDS:
        return False
    raise ConfigValidationError(f"`{raw}` is not a yes/no value. Try `true` or `false`.")


COLOR_HINT = "Use a 6-digit hex color code, like `#5865F2`, `5865F2`, or `0x5865F2`."

_COLOR_PATTERN = re.compile(r"\A(?:#|0[xX])?(?P<digits>[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\Z")


def parse_color(raw: str) -> int:
    """Parse a hex color code into the integer Discord wants.

    Accepts `#5865F2`, `5865F2`, `0x5865F2`, and the 3-digit shorthand `#58F`. A bare run
    of digits is read as hex, never as a decimal integer.
    """
    value = raw.strip()
    match = _COLOR_PATTERN.fullmatch(value)
    if match is None:
        if value.startswith("#"):
            stripped = value[1:]
        elif value[:2].lower() == "0x":
            stripped = value[2:]
        else:
            stripped = value
        if (
            stripped
            and len(stripped) not in (3, 6)
            and all(character in "0123456789abcdefABCDEF" for character in stripped)
        ):
            raise ConfigValidationError(
                f"`{raw}` has {len(stripped)} hex digits; a color code needs 6 (or 3 for "
                f"shorthand). {COLOR_HINT}"
            )
        raise ConfigValidationError(f"`{raw}` is not a hex color code. {COLOR_HINT}")

    digits = match.group("digits")
    if len(digits) == 3:
        digits = "".join(character * 2 for character in digits)
    return int(digits, 16)


MIN_SNOWFLAKE_DIGITS = 17
MAX_SNOWFLAKE_DIGITS = 20

_SNOWFLAKE_PATTERN = re.compile(r"\A[0-9]+\Z")
_CHANNEL_MESSAGE_PATTERN = re.compile(r"\A[0-9]+-(?P<message>[0-9]+)\Z")


def parse_message_id(raw: str) -> int:
    """Parse a Discord message ID, accepting the `channel-message` copy-link form.

    Snowflakes exceed what a slash command integer option can carry, so the ID arrives
    as a string. "Copy ID" gives a bare number, while "Copy Message Link" pastes a URL;
    both are accepted, along with the `channelid-messageid` shape that Discord's
    shift-click copy produces.
    """
    value = raw.strip()
    if "/" in value:
        value = value.rstrip("/").rsplit("/", 1)[-1]
    dashed = _CHANNEL_MESSAGE_PATTERN.fullmatch(value)
    if dashed:
        value = dashed.group("message")
    if not _SNOWFLAKE_PATTERN.fullmatch(value):
        raise ConfigValidationError(
            f"`{raw}` is not a message ID. Right-click the message and choose **Copy Message "
            "Link**, or turn on Developer Mode and choose **Copy Message ID**."
        )
    if not MIN_SNOWFLAKE_DIGITS <= len(value) <= MAX_SNOWFLAKE_DIGITS:
        raise ConfigValidationError(
            f"`{value}` has {len(value)} digits, so it isn't a Discord message ID -- those are "
            f"{MIN_SNOWFLAKE_DIGITS}-{MAX_SNOWFLAKE_DIGITS} digits long."
        )
    return int(value)


def parse_status_type(raw: str) -> str:
    value = raw.strip().capitalize()
    if value not in STATUS_TYPES:
        raise ConfigValidationError(
            f"`{raw}` is not a status type. Choose one of: {', '.join(STATUS_TYPES)}."
        )
    return value


def coerce_setting(key: str, raw: str) -> Any:
    """Turn the raw string from a slash command into the stored value for `key`."""
    kind = SETTABLE.get(key)
    if kind is None:
        raise ConfigValidationError(f"`{key}` is not a live-editable setting.")
    if kind == "bool":
        return parse_bool(raw)
    if kind == "color":
        return parse_color(raw)
    if kind == "status_type":
        return parse_status_type(raw)
    return raw


def setting_label(key: str) -> str:
    """The human-readable name for a setting, falling back to the raw key."""
    spec = SPECS_BY_KEY.get(key)
    return spec.label if spec else key


def format_setting_value(key: str, value: Any) -> str:
    """Render a stored setting the way a human expects to read it."""
    if value is None or value == "":
        return "*not set*"
    kind = SETTABLE.get(key)
    if kind == "color" and isinstance(value, int):
        return f"#{value:06X}"
    if kind == "bool":
        return "Enabled" if value else "Disabled"
    return str(value)


def validate_type_fields(key: str, label: str, description: str) -> None:
    """Check one ticket type against Discord's select-option limits."""
    if not key.strip():
        raise ConfigValidationError("The type key cannot be empty.")
    if key != key.strip():
        raise ConfigValidationError("The type key cannot start or end with whitespace.")
    for field_name, value in (("key", key), ("label", label), ("description", description)):
        if not value.strip():
            raise ConfigValidationError(f"The {field_name} cannot be empty.")
        if len(value) > MAX_SELECT_FIELD_LENGTH:
            raise ConfigValidationError(
                f"The {field_name} is {len(value)} characters; Discord allows at most "
                f"{MAX_SELECT_FIELD_LENGTH}."
            )


def validate_room_for_new_type(existing_keys: tuple[str, ...], new_key: str) -> None:
    """Reject a new type that would push the creation dropdown past Discord's limit."""
    if new_key in existing_keys:
        raise ConfigValidationError(f"A ticket type with the key `{new_key}` already exists.")
    if len(existing_keys) >= MAX_TICKET_TYPES:
        raise ConfigValidationError(
            f"There are already {len(existing_keys)} ticket types, and Discord select menus "
            f"allow at most {MAX_TICKET_TYPES}. Remove one first."
        )


def describe_removal_block(type_key: str, open_tickets: int) -> str:
    """The message shown when a type cannot be removed because tickets still use it."""
    return (
        f"`{type_key}` still has {open_tickets} open ticket(s). Removing it would leave them "
        "without staff role permissions. Close them first, or re-run with `force: True`."
    )
