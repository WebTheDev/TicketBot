from typing import Dict, Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Main Config
    bot_token: str = Field(
        description="Discord bot token used to log the bot in.",
    )
    bot_status_type: str = Field(
        default="",
        description="Bot Status Type (Ex. Playing, Watching, Listening, or Streaming)",
    )
    bot_status_message: str = Field(
        default="",
        description="The message that is shown on the bots activity",
    )
    guild_id: int = Field(
        description="ID of the Guild the the bot is running in",
    )
    ticket_logs_channel_id: int = Field(
        description="ID of the Channel to send system logs to",
    )
    ticket_transcript_channel_id: int = Field(
        description="ID of the Channel to send ticket transcripts to",
    )
    database_url: str = Field(
        description=(
            "PostgreSQL connection string for the ticket database. Must use the asyncpg "
            "driver, e.g. postgresql+asyncpg://user:password@localhost:5432/ticketbot"
        ),
    )
    debug_log_send_id: int = Field(
        description="ID of the Bot Owner to send debug information to",
    )

    # Ticket Creation/Options Config
    id_of_channel_to_send_ticket_creation_embed: int = Field(
        description="ID of the Channel to send the Create a ticket embed to",
    )
    id_of_message_for_ticket_creation: int = Field(
        default=0,
        description=(
            "LEGACY: the ticket-creation embed's message ID now lives in PostgreSQL as "
            "the `creation_message_id` setting and is managed by the bot. This field is "
            "read once, during first-run seeding, and is not required for the .env unless if a embed already exists."
        ),
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

    # LEGACY -- everything from here down now lives in PostgreSQL and is edited with the
    # /config commands. These fields are read once, during first-run seeding, so an
    # existing install carries its settings over; after that they are ignored and can be
    # removed from .env. See utils/runtime_config.py.
    options_dict: Dict[str, Tuple[str, str, str]] = Field(
        default={
            "Option 1": ("Sales 💲", "sales", "Create a sales related ticket."),
            "Option 2": ("Support ❓", "support", "Create a support related ticket."),
            "Option 3": ("Report ✋", "staff", "Create a ticket to speak with a member of staff."),
        },
        description=(
            "This is the ticket options dictionary. It defines the different types of tickets "
            "that users can create. A ticket option definition should look something like this: "
            '"Option #": ("Title of Option", "Type of Option", "Description of Option")'
        ),
    )

    channel_perms: Dict[str, Tuple[int, ...]] = Field(
        default={
            "sales": (0,),
            "support": (0, 0),
            "staff": (0, 0),
        },
        description=(
            "This is the ticket channel perms dictionary. This dictionary defines what roles "
            'will have access to each type of Ticket Channel. Each type can support multiple '
            'role IDs. Each entry into the definition should look something like this: '
            '"Type of Option": (ROLEID1, ROLEID2). IMPORTANT: MAKE SURE THAT THE TYPE OF OPTION '
            "IS THE SAME AS THE TYPE OF OPTION THAT WAS DEFINED IN THE TICKET OPTIONS DEFINITION. "
            "IF NOT, PERMISSIONS WILL NOT BE SET CORRECTLY AND THE BOT WILL NOT WORK RIGHT."
        ),
    )

    ticket_type_allowed_to_create_private_channels: str = Field(
        default="staff",
        description=(
            "Set this to be the type of option (roles) as defined in the ticket channel perms "
            "dictionary that can use the /create command."
        ),
    )
    multiple_tickets_allowed: bool = Field(
        default=False,
        description=(
            "Set this to True if you would like members to be able to have multiple tickets "
            "open at once (otherwise set to False)."
        ),
    )
    dm_ticket_copies: bool = Field(
        default=True,
        description="Set this to True if you would like the bot to dm Ticket Creators transcript copies of their ticket.",
    )

    # Embed Config
    footer_of_embeds: str = Field(
        default="",
        description="Set a custom embed footer of all embedded messages here!",
    )
    embed_color: int = Field(
        default=0xFFFFFF,
        description="Set a custom hex color code for all embeds! Make sure to keep the 0x!",
    )


settings = Settings()
