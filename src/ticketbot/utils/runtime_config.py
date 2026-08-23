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

# Scalars seeded from `.env` on first run. `creation_message_id` is handled separately:
# it is the renamed `id_of_message_for_ticket_creation`, and a value of 0 (the old
# "not yet posted" placeholder) must become None rather than a bogus message ID.
SEEDED_FROM_ENV: tuple[str, ...] = (
    "bot_status_type",
    "bot_status_message",
    "embed_color",
    "footer_of_embeds",
    "multiple_tickets_allowed",
    "dm_ticket_copies",
    "ticket_type_allowed_to_create_private_channels",
)


class RuntimeConfigNotLoaded(RuntimeError):
    """Raised when a database-backed setting is read before `refresh()` has run."""


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
        """Seed the config tables from `.env` the first time the bot runs.

        Does nothing once any ticket type or setting exists, so this is safe to call on
        every startup. Returns a human-readable list of what was seeded, for logging.
        """
        await self.refresh()
        if self._types or self._settings:
            return []

        types: list[dict[str, Any]] = []
        roles: list[dict[str, Any]] = []
        legacy_options = getattr(env_settings, "options_dict", None) or {}
        legacy_perms = getattr(env_settings, "channel_perms", None) or {}

        for position, preset in enumerate(legacy_options.values()):
            label, key, description = preset
            types.append(
                {"key": key, "label": label, "description": description, "position": position}
            )

        seeded_keys = {entry["key"] for entry in types}
        for type_key, role_ids in legacy_perms.items():
            if type_key not in seeded_keys:
                # The old config allowed channel_perms to name a type that options_dict
                # never defined; such entries were dead weight and cannot be represented
                # now that the roles table has a foreign key.
                continue
            for role_id in role_ids if isinstance(role_ids, (list, tuple)) else (role_ids,):
                if role_id:  # 0 was the placeholder in the shipped config
                    roles.append({"type_key": type_key, "role_id": role_id})

        scalars: dict[str, Any] = {
            key: getattr(env_settings, key) for key in SEEDED_FROM_ENV if hasattr(env_settings, key)
        }
        legacy_message_id = getattr(env_settings, "id_of_message_for_ticket_creation", 0)
        scalars["creation_message_id"] = legacy_message_id or None
        scalars.update(DB_MANAGED_DEFAULTS)

        await ConfigRepository.seed(types, roles, scalars)
        await self.refresh()

        summary = [f"{len(types)} ticket type(s)", f"{len(roles)} role assignment(s)", f"{len(scalars)} setting(s)"]
        return summary


settings = RuntimeConfig()
