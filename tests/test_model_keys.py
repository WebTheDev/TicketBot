"""Tests for the primary-key contract shared by every table.

Every model is keyed on a surrogate BIGINT identity column. The natural keys those
tables used to be keyed on must stay UNIQUE: the application still addresses rows by
them, and the `ON CONFLICT` upserts in `utils/database.py` need a unique index to use
as their conflict target. Losing one of those constraints would not fail loudly -- it
would quietly allow duplicate tickets or settings -- so it is asserted here.
"""

import pytest
from sqlalchemy import BigInteger

from ticketbot.models import Base, BotSetting, Ticket, TicketType, TicketTypeRole

ALL_MODELS = (Ticket, TicketType, TicketTypeRole, BotSetting)

# The natural key each table used to be keyed on, which must remain UNIQUE.
NATURAL_KEYS = {
    Ticket: ("channel_id",),
    TicketType: ("key",),
    TicketTypeRole: ("type_key", "role_id"),
    BotSetting: ("key",),
}


def unique_column_sets(model) -> set[frozenset[str]]:
    """Every column combination the table guarantees to be unique."""
    sets = {
        frozenset(constraint.columns.keys())
        for constraint in model.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    sets |= {frozenset(index.columns.keys()) for index in model.__table__.indexes if index.unique}
    return sets


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__tablename__)
class TestSurrogatePrimaryKeys:
    def test_primary_key_is_a_single_id_column(self, model):
        primary_key = list(model.__table__.primary_key.columns)
        assert [column.name for column in primary_key] == ["id"]

    def test_primary_key_is_bigint(self, model):
        assert isinstance(model.__table__.c.id.type, BigInteger)

    def test_primary_key_is_generated_by_the_database(self, model):
        # Without an identity/sequence the application would have to invent IDs itself.
        column = model.__table__.c.id
        assert column.identity is not None or column.autoincrement is True

    def test_natural_key_is_still_unique(self, model):
        expected = frozenset(NATURAL_KEYS[model])
        assert expected in unique_column_sets(model), (
            f"{model.__tablename__} no longer guarantees {sorted(expected)} is unique; "
            "the ON CONFLICT upserts in utils/database.py depend on it"
        )

    def test_natural_key_columns_are_not_nullable(self, model):
        for column_name in NATURAL_KEYS[model]:
            assert model.__table__.c[column_name].nullable is False


class TestSchemaWiring:
    def test_every_table_is_registered_on_the_metadata(self):
        registered = set(Base.metadata.tables)
        assert registered == {model.__tablename__ for model in ALL_MODELS}

    def test_ticket_type_roles_still_cascades_from_ticket_types(self):
        # Deleting a type must take its role rows with it; /config types remove relies on it.
        foreign_keys = list(TicketTypeRole.__table__.c.type_key.foreign_keys)
        assert len(foreign_keys) == 1
        assert foreign_keys[0].column is TicketType.__table__.c.key
        assert foreign_keys[0].ondelete == "CASCADE"

    def test_the_foreign_key_target_is_itself_unique(self):
        # A foreign key can only reference a uniquely-constrained column.
        assert frozenset({"key"}) in unique_column_sets(TicketType)
