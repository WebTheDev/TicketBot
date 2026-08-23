"""Tests for the live-config overlay.

These exercise `RuntimeConfig` against a stubbed repository, so no database is needed.
The behavior that matters most here is the overlay contract: DB-managed keys come from
the cache and never silently fall back to stale `.env` values.
"""

import pytest

from ticketbot.models import TicketType
from ticketbot.utils import runtime_config as runtime_config_module
from ticketbot.utils.runtime_config import DB_MANAGED_KEYS, RuntimeConfig, RuntimeConfigNotLoaded


def make_type(key: str, position: int, label: str | None = None) -> TicketType:
    return TicketType(
        key=key, label=label or key.title(), description=f"A {key} ticket.", position=position
    )


class StubRepository:
    """Stands in for ConfigRepository, recording writes instead of issuing SQL."""

    def __init__(self, types=None, roles=None, settings=None):
        self.types = types or []
        self.roles = roles or []
        self.settings = settings or {}
        self.seeded = None

    async def all_types(self):
        return list(self.types)

    async def all_roles(self):
        return list(self.roles)

    async def all_settings(self):
        return dict(self.settings)

    async def set_setting(self, key, value):
        self.settings[key] = value

    async def seed(self, types, roles, scalars):
        self.seeded = {"types": types, "roles": roles, "scalars": scalars}
        self.types = [make_type(entry["key"], entry["position"], entry["label"]) for entry in types]
        self.roles = [_Role(entry["type_key"], entry["role_id"]) for entry in roles]
        self.settings = dict(scalars)


class _Role:
    def __init__(self, type_key, role_id):
        self.type_key = type_key
        self.role_id = role_id


@pytest.fixture
def stub(monkeypatch):
    repository = StubRepository()
    monkeypatch.setattr(runtime_config_module, "ConfigRepository", repository)
    return repository


class TestUnloadedCache:
    def test_reading_a_live_setting_before_loading_raises(self, stub):
        config = RuntimeConfig()
        # The whole point of raising here is that falling back to .env would silently
        # serve a value the operator already changed.
        with pytest.raises(RuntimeConfigNotLoaded, match="embed_color"):
            _ = config.embed_color

    def test_reading_ticket_types_before_loading_raises(self, stub):
        config = RuntimeConfig()
        with pytest.raises(RuntimeConfigNotLoaded):
            _ = config.ticket_types

    def test_env_only_settings_still_resolve(self, stub):
        # bot_token never moved to the database, so it must work without a refresh.
        config = RuntimeConfig()
        assert config.bot_token == "test-token"


class TestOverlayResolution:
    async def test_live_settings_come_from_the_database(self, stub):
        stub.settings = {"embed_color": 0x5865F2, "footer_of_embeds": "From Postgres"}
        config = RuntimeConfig()
        await config.refresh()

        assert config.embed_color == 0x5865F2
        assert config.footer_of_embeds == "From Postgres"

    async def test_env_settings_fall_through(self, stub):
        config = RuntimeConfig()
        await config.refresh()

        assert config.guild_id == 1
        assert config.archived_tickets_category_id == 9

    async def test_a_write_is_visible_immediately(self, stub):
        stub.settings = {"embed_color": 0xFFFFFF}
        config = RuntimeConfig()
        await config.refresh()
        assert config.embed_color == 0xFFFFFF

        # This is the no-restart guarantee: set it, read it, no reload in between.
        await config.set_value("embed_color", 0x000000)
        assert config.embed_color == 0x000000

    async def test_unset_live_setting_reads_as_none(self, stub):
        config = RuntimeConfig()
        await config.refresh()
        assert config.creation_message_id is None

    def test_every_db_managed_key_is_covered_by_the_overlay(self):
        # Guards against adding a key to DB_MANAGED_KEYS but forgetting it can now be
        # read before the cache loads.
        config = RuntimeConfig()
        for key in DB_MANAGED_KEYS:
            with pytest.raises(RuntimeConfigNotLoaded):
                getattr(config, key)


class TestTicketTypesAndRoles:
    async def test_types_keep_their_configured_order(self, stub):
        stub.types = [make_type("support", 0), make_type("sales", 1), make_type("staff", 2)]
        config = RuntimeConfig()
        await config.refresh()

        assert [t.key for t in config.ticket_types] == ["support", "sales", "staff"]
        assert config.known_type_keys() == ("support", "sales", "staff")

    async def test_channel_perms_keeps_the_legacy_shape(self, stub):
        # The 14 existing call sites index this dict directly, so its shape is a contract.
        stub.types = [make_type("sales", 0), make_type("support", 1)]
        stub.roles = [_Role("sales", 111), _Role("sales", 222), _Role("support", 333)]
        config = RuntimeConfig()
        await config.refresh()

        assert config.channel_perms == {"sales": (111, 222), "support": (333,)}

    async def test_a_type_with_no_roles_is_present_but_empty(self, stub):
        stub.types = [make_type("sales", 0)]
        config = RuntimeConfig()
        await config.refresh()

        assert config.channel_perms == {"sales": ()}
        assert config.roles_for("sales") == ()

    async def test_roles_for_an_unknown_type_is_empty_not_an_error(self, stub):
        # A ticket whose type was deleted must still be usable: the old code raised
        # KeyError here, which the surrounding handlers did not catch.
        stub.types = [make_type("sales", 0)]
        config = RuntimeConfig()
        await config.refresh()

        assert config.roles_for("deleted-type") == ()

    async def test_callers_cannot_mutate_the_cache(self, stub):
        stub.types = [make_type("sales", 0)]
        stub.roles = [_Role("sales", 111)]
        config = RuntimeConfig()
        await config.refresh()

        config.channel_perms["sales"] = (999,)
        config.ticket_types.clear()

        assert config.channel_perms == {"sales": (111,)}
        assert len(config.ticket_types) == 1


class TestBootstrap:
    async def test_seeds_types_roles_and_scalars_from_env(self, stub):
        config = RuntimeConfig()
        summary = await config.bootstrap()

        assert summary  # non-empty means it seeded
        seeded_types = {entry["key"] for entry in stub.seeded["types"]}
        assert seeded_types == {"sales", "support", "staff"}
        assert stub.seeded["scalars"]["embed_color"] == 0xFFFFFF
        assert config.known_type_keys() == ("sales", "support", "staff")

    async def test_placeholder_role_ids_are_not_seeded(self, stub):
        # The shipped config used 0 as the "fill this in" placeholder for role IDs.
        await RuntimeConfig().bootstrap()
        assert stub.seeded["roles"] == []

    async def test_placeholder_message_id_becomes_none(self, stub):
        # 0 meant "not posted yet"; it must not be stored as a real message ID or the
        # bot would try to edit message 0 instead of posting a new embed.
        config = RuntimeConfig()
        await config.bootstrap()
        assert config.creation_message_id is None

    async def test_does_nothing_when_types_already_exist(self, stub):
        stub.types = [make_type("existing", 0)]
        config = RuntimeConfig()

        assert await config.bootstrap() == []
        assert stub.seeded is None
        assert config.known_type_keys() == ("existing",)

    async def test_does_nothing_when_only_settings_exist(self, stub):
        # A install that removed all its ticket types must not be re-seeded from .env.
        stub.settings = {"embed_color": 0x123456}
        config = RuntimeConfig()

        assert await config.bootstrap() == []
        assert stub.seeded is None


class TestAutoPostCreationEmbedDefault:
    """A key added after release must not read as "off" on installs seeded without it."""

    async def test_defaults_to_true_when_absent(self, stub):
        stub.settings = {"embed_color": 0xFFFFFF}
        config = RuntimeConfig()
        await config.refresh()
        assert config.auto_post_creation_embed is True

    async def test_a_stored_false_wins_over_the_default(self, stub):
        stub.settings = {"auto_post_creation_embed": False}
        config = RuntimeConfig()
        await config.refresh()
        assert config.auto_post_creation_embed is False

    async def test_bootstrap_seeds_it(self, stub):
        config = RuntimeConfig()
        await config.bootstrap()
        assert stub.seeded["scalars"]["auto_post_creation_embed"] is True

    async def test_it_is_db_managed(self, stub):
        assert "auto_post_creation_embed" in DB_MANAGED_KEYS
        with pytest.raises(RuntimeConfigNotLoaded):
            _ = RuntimeConfig().auto_post_creation_embed
