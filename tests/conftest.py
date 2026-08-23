"""Shared test setup.

`config.Settings` validates at import time and `utils.database` builds an engine from
the DSN, so the environment has to be populated before any bot module is imported.
These values are placeholders: the unit tests never open a connection.

The assignments are unconditional on purpose. Environment variables take precedence over
the `.env` file in pydantic-settings, so setting every field here makes the tests
hermetic -- they behave the same whether or not the developer has a populated `.env` or
exported settings in their shell. Using `setdefault` here would let a real environment
leak in and change what the tests assert against.
"""

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/ticketbot_test"
os.environ["BOT_TOKEN"] = "test-token"
os.environ["GUILD_ID"] = "1"
os.environ["TICKET_LOGS_CHANNEL_ID"] = "2"
os.environ["TICKET_TRANSCRIPT_CHANNEL_ID"] = "3"
os.environ["DEBUG_LOG_SEND_ID"] = "4"
os.environ["ID_OF_CHANNEL_TO_SEND_TICKET_CREATION_EMBED"] = "5"
os.environ["ID_OF_MESSAGE_FOR_TICKET_CREATION"] = "0"
os.environ["ACTIVE_TICKETS_CATEGORY_ID"] = "7"
os.environ["ON_HOLD_TICKETS_CATEGORY_ID"] = "8"
os.environ["ARCHIVED_TICKETS_CATEGORY_ID"] = "9"

# The migrated legacy settings, pinned so the bootstrap tests assert against known
# values rather than whatever the developer happens to have configured.
os.environ["EMBED_COLOR"] = str(0xFFFFFF)
os.environ["FOOTER_OF_EMBEDS"] = ""
os.environ["BOT_STATUS_TYPE"] = "Playing"
os.environ["BOT_STATUS_MESSAGE"] = ""
os.environ["MULTIPLE_TICKETS_ALLOWED"] = "False"
os.environ["DM_TICKET_COPIES"] = "True"
os.environ["TICKET_TYPE_ALLOWED_TO_CREATE_PRIVATE_CHANNELS"] = "staff"
