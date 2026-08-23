"""Live, database-backed configuration.

Most of the bot's settings used to be frozen into the pydantic `Settings` object at
import time, so changing one meant editing `.env` and restarting. The settings an
operator actually retunes now live in PostgreSQL, and this module serves them from an
in-memory cache that is reloaded on startup and after every write.

`RuntimeConfig` is an *overlay*: attributes listed in `DB_MANAGED_KEYS` are answered
from the cache, and everything else (the bot token, the DSN, the channel and category
IDs) falls through to the pydantic settings loaded from `.env`. Because it keeps the
name `settings`, existing call sites like `settings.embed_color` did not have to
change -- only the import line did.

One deliberate sharp edge: a DB-managed key never falls back to `.env`. If the cache
was never loaded, reading one raises `RuntimeConfigNotLoaded` rather than silently
returning a stale `.env` value, so a missed `refresh()` fails loudly.
"""

import json
import os
from typing import Any

from ticketbot.config import settings as env_settings
from ticketbot.models import TicketType
from ticketbot.utils.database import ConfigRepository

# Settings that live in PostgreSQL and can be changed without a restart. The names
# match the pydantic field names they replaced, which is what lets the overlay resolve
# them by attribute access.
DB_MANAGED_KEYS: frozenset[str] = frozenset(
    {
        "bot_status_type",
        "bot_status_message",
        "embed_color",
        "footer_of_embeds",
        "multiple_tickets_allowed",
        "dm_ticket_copies",
        "ticket_type_allowed_to_create_private_channels",
        "creation_message_id",
        "auto_post_creation_embed",
    }
)

# Defaults for DB-managed keys that were added after the first release. An install
# seeded before the key existed has no row for it, and `None` would read as "off"; these
# keep such an install on the behavior it already had.
DB_MANAGED_DEFAULTS: dict[str, Any] = {
    "auto_post_creation_embed": True,
}

# What a brand-new install starts with. These used to be defaults on the pydantic
# Settings fields; they moved here when those fields were removed, because the values a
# fresh database is seeded with are a property of the database layer, not of `.env`.
DEFAULT_TICKET_TYPES: tuple[dict[str, Any], ...] = (
    {"key": "sales", "label": "Sales 💲", "description": "Create a sales related ticket."},
    {"key": "support", "label": "Support ❓", "description": "Create a support related ticket."},
    {
        "key": "staff",
        "label": "Report ✋",
        "description": "Create a ticket to speak with a member of staff.",
    },
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "bot_status_type": "Playing",
    "bot_status_message": "",
    "embed_color": 0xFFFFFF,
    "footer_of_embeds": "",
    "multiple_tickets_allowed": False,
    "dm_ticket_copies": True,
    "ticket_type_allowed_to_create_private_channels": "staff",
}

# Settings that used to live in `.env` and now live in PostgreSQL, mapped to the
# environment variable an older install may still be carrying. `bootstrap()` reads these
# straight from the environment rather than from the pydantic Settings, because Settings
# deliberately no longer declares them -- see `ticketbot/config.py`.
LEGACY_ENV_KEYS: dict[str, str] = {
    "bot_status_type": "BOT_STATUS_TYPE",
    "bot_status_message": "BOT_STATUS_MESSAGE",
    "embed_color": "EMBED_COLOR",
    "footer_of_embeds": "FOOTER_OF_EMBEDS",
    "multiple_tickets_allowed": "MULTIPLE_TICKETS_ALLOWED",
    "dm_ticket_copies": "DM_TICKET_COPIES",
    "ticket_type_allowed_to_create_private_channels": (
        "TICKET_TYPE_ALLOWED_TO_CREATE_PRIVATE_CHANNELS"
    ),
}

LEGACY_MESSAGE_ID_ENV = "ID_OF_MESSAGE_FOR_TICKET_CREATION"
LEGACY_OPTIONS_ENV = "OPTIONS_DICT"
LEGACY_PERMS_ENV = "CHANNEL_PERMS"


class RuntimeConfigNotLoaded(RuntimeError):
    """Raised when a database-backed setting is read before `refresh()` has run."""


def _legacy_env(name: str) -> str | None:
    raw = os.environ.get(name)
    return raw if raw is not None and raw.strip() != "" else None


def legacy_scalar_settings() -> dict[str, Any]:
    """Migrated scalars still present in the environment, coerced to their stored types.

    A value that cannot be parsed is skipped rather than raising: a typo in a setting
    that is about to become editable over Discord is not worth refusing to start over.
    """
    from ticketbot.utils.config_validation import ConfigValidationError, SETTABLE, coerce_setting

    found: dict[str, Any] = {}
    for key, env_name in LEGACY_ENV_KEYS.items():
        raw = _legacy_env(env_name)
        if raw is None:
            continue
        if key == "embed_color":
            color = _legacy_color(raw)
            if color is not None:
                found[key] = color
            continue
        try:
            found[key] = coerce_setting(key, raw) if key in SETTABLE else raw
        except ConfigValidationError:
            continue
    return found


def _legacy_color(raw: str) -> int | None:
    """Parse a colour the way the removed pydantic `int` field did.

    `/config set` requires a hex code, but this field used to be a plain int, so a
    long-standing `.env` may hold either `0xFFFFFF` or its decimal equivalent. Reading it
    with the stricter Discord-facing rule would silently discard the decimal form.
    """
    try:
        value = int(raw.strip(), 0)
    except ValueError:
        from ticketbot.utils.config_validation import ConfigValidationError, parse_color

        try:
            return parse_color(raw)
        except ConfigValidationError:
            return None
    return value if 0 <= value <= 0xFFFFFF else None


def legacy_creation_message_id() -> int | None:
    """The pre-move creation embed ID, if one was recorded.

    0 was the "not posted yet" placeholder and must become None, or the bot would try to
    edit message 0 instead of establishing an embed.
    """
    raw = _legacy_env(LEGACY_MESSAGE_ID_ENV)
    if raw is None:
        return None
    try:
        return int(raw) or None
    except ValueError:
        return None


def legacy_ticket_types() -> list[dict[str, Any]]:
    """Ticket types from a legacy `OPTIONS_DICT`, in its `(label, key, description)` shape."""
    raw = _legacy_env(LEGACY_OPTIONS_ENV)
    if raw is None:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    types: list[dict[str, Any]] = []
    for position, preset in enumerate(parsed.values() if isinstance(parsed, dict) else parsed):
        if not isinstance(preset, (list, tuple)) or len(preset) != 3:
            continue
        label, key, description = preset
        types.append(
            {"key": key, "label": label, "description": description, "position": position}
        )
    return types


def legacy_type_roles(known_keys: set[str]) -> list[dict[str, Any]]:
    """Role assignments from a legacy `CHANNEL_PERMS`, limited to types that exist."""
    raw = _legacy_env(LEGACY_PERMS_ENV)
    if raw is None:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, dict):
        return []
    roles: list[dict[str, Any]] = []
    for type_key, role_ids in parsed.items():
        # The old config let channel_perms name a type options_dict never defined. The
        # roles table has a foreign key now, so such an entry would fail to insert.
        if type_key not in known_keys:
            continue
        for role_id in role_ids if isinstance(role_ids, (list, tuple)) else (role_ids,):
            if role_id:  # 0 was the "fill this in" placeholder
                roles.append({"type_key": type_key, "role_id": int(role_id)})
    return roles


class RuntimeConfig:
    """Attribute-style access to live settings, falling back to `.env` for the rest."""

    def __init__(self) -> None:
        self._loaded = False
        self._settings: dict[str, Any] = {}
        self._types: list[TicketType] = []
        self._roles: dict[str, tuple[int, ...]] = {}

    # -- loading ---------------------------------------------------------------

    async def refresh(self) -> None:
        """Reload every cache from the database."""
        types = await ConfigRepository.all_types()
        roles = await ConfigRepository.all_roles()
        stored = await ConfigRepository.all_settings()

        role_map: dict[str, tuple[int, ...]] = {ticket_type.key: () for ticket_type in types}
        for role in roles:
            role_map[role.type_key] = role_map.get(role.type_key, ()) + (role.role_id,)

        self._types = types
        self._roles = role_map
        self._settings = stored
        self._loaded = True

    @property
    def loaded(self) -> bool:
        return self._loaded

    # -- reads -----------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        # Only reached for attributes not found normally, so the private fields above
        # never route through here.
        if name in DB_MANAGED_KEYS:
            if not self._loaded:
                raise RuntimeConfigNotLoaded(
                    f"Tried to read live setting {name!r} before the config cache was loaded. "
                    "Call `await settings.refresh()` during startup."
                )
            if name in self._settings:
                return self._settings[name]
            return DB_MANAGED_DEFAULTS.get(name)
        return getattr(env_settings, name)

    @property
    def ticket_types(self) -> list[TicketType]:
        """Ticket types in dropdown order. Replaces the old `options_dict`."""
        self._require_loaded()
        return list(self._types)

    @property
    def channel_perms(self) -> dict[str, tuple[int, ...]]:
        """Role IDs per ticket type, in the same shape the old `channel_perms` had."""
        self._require_loaded()
        return dict(self._roles)

    def roles_for(self, type_key: str) -> tuple[int, ...]:
        """Roles for a type, or an empty tuple if the type no longer exists.

        Returning empty rather than raising matters for tickets whose type was deleted
        while they were still open: their buttons degrade to "no extra roles" instead
        of failing the interaction with a KeyError.
        """
        self._require_loaded()
        return self._roles.get(type_key, ())

    def known_type_keys(self) -> tuple[str, ...]:
        self._require_loaded()
        return tuple(ticket_type.key for ticket_type in self._types)

    def _require_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeConfigNotLoaded(
                "The config cache has not been loaded. Call `await settings.refresh()` during startup."
            )

    # -- writes ----------------------------------------------------------------

    async def set_value(self, key: str, value: Any) -> None:
        """Persist one scalar setting and reload the cache."""
        await ConfigRepository.set_setting(key, value)
        await self.refresh()

    async def bootstrap(self) -> list[str]:
        """Seed the config tables the first time the bot runs.

        Seeds the shipped defaults, letting any leftover `.env` values from before these
        settings moved to PostgreSQL take precedence, so an upgrading install keeps the
        look it already had. Does nothing once any ticket type or setting exists, so this
        is safe to call on every startup. Returns a summary for logging.
        """
        await self.refresh()
        if self._types or self._settings:
            return []

        types = legacy_ticket_types() or [
            {**preset, "position": position}
            for position, preset in enumerate(DEFAULT_TICKET_TYPES)
        ]
        roles = legacy_type_roles({entry["key"] for entry in types})

        scalars: dict[str, Any] = {**DEFAULT_SETTINGS, **DB_MANAGED_DEFAULTS}
        scalars.update(legacy_scalar_settings())
        scalars["creation_message_id"] = legacy_creation_message_id()

        await ConfigRepository.seed(types, roles, scalars)
        await self.refresh()

        return [
            f"{len(types)} ticket type(s)",
            f"{len(roles)} role assignment(s)",
            f"{len(scalars)} setting(s)",
        ]


settings = RuntimeConfig()
