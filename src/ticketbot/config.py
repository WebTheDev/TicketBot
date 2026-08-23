"""The `.env` settings, and only those.

A value belongs here if the bot cannot function without it before a database connection
exists, or if changing it means restarting anyway.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Credentials and storage
    bot_token: str = Field(
        description="Discord bot token used to log the bot in.",
    )
    database_url: str = Field(
        description=(
            "PostgreSQL connection string for the ticket database. Must use the asyncpg "
            "driver, e.g. postgresql+asyncpg://user:password@localhost:5432/ticketbot"
        ),
    )

    # Where the bot lives. Moving any of these means moving channels, so a restart is
    # expected regardless.
    guild_id: int = Field(
        description="ID of the Guild the bot is running in",
    )
    ticket_logs_channel_id: int = Field(
        description="ID of the Channel to send system logs to",
    )
    ticket_transcript_channel_id: int = Field(
        description="ID of the Channel to send ticket transcripts to",
    )
    debug_log_send_id: int = Field(
        description="ID of the Bot Owner to send debug information to",
    )
    id_of_channel_to_send_ticket_creation_embed: int = Field(
        description="ID of the Channel to send the Create a ticket embed to",
    )
    active_tickets_category_id: int = Field(
        description="ID of the active tickets category",
    )
    on_hold_tickets_category_id: int = Field(
        description="ID of the onhold tickets category",
    )
    archived_tickets_category_id: int = Field(
        description="ID of the archived tickets category",
    )


settings = Settings()
