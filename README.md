### Discord-TicketBot 📝

- A discord bot that is designed to manage and create ticket channels on behalf of server members using the [Rapptz discord.py API](https://github.com/Rapptz/discord.py).
- Compiled on Python 3.10.  
- Tested to work on both Windows and Linux (Python 3.8.1 or newer).
- Optionally, you can run this [bot in a docker environment](https://github.com/WebTheDev/TicketBot/tree/docker).

---
### Screenshots

<p align="center"><img src="https://webthedev.me/assets/img/ticketbot-demo-1.gif" /></p><p align="center"><img src="https://webthedev.me/assets/img/ticketbot-demo-2-1.gif" /></p>

---
### Features
- Slash Commands and Interactions
- The ability to place Tickets in different categories depending on their status (Active, Onhold, Archived)
- Claim, Rename, Add, or Remove members from a ticket channel
- System-Logging
- Embedded Ticket Transcription Logs (using [chat-exporter](https://pypi.org/project/chat-exporter/))
- Customizable Embeds
- Customizable Ticket Options that members can select while creating tickets
- Complex ticket permission system that can be customized per ticket option
- Embedded "Create a ticket" button
- GUI-like Ticket Options menu
- A **/create** command that staff can use to manually create tickets
- Something else that I'm probably missing!

---
### Requirements
- [Python](https://www.python.org/downloads/) 3.14 or newer, and [uv](https://docs.astral.sh/uv/) for dependency management.
- A [PostgreSQL](https://www.postgresql.org/download/) database (14 or newer). The bot stores every ticket there and reaches it asynchronously via [asyncpg](https://pypi.org/project/asyncpg/).
- Python packages are declared in `pyproject.toml` and installed with `uv sync`: [discord.py](https://pypi.org/project/discord.py/), [chat-exporter](https://pypi.org/project/chat-exporter/), [SQLAlchemy](https://pypi.org/project/SQLAlchemy/), [asyncpg](https://pypi.org/project/asyncpg/), and [Alembic](https://pypi.org/project/alembic/).

---
### Setup
- Place all bot related files into a seperate folder (this is **important** to do so, or else the python compiler will not be able to find the bot files necessary for the ticket bot to work)
- Create three categories in the discord server that the bot will be running in labeled: Active, OnHold, and Archived (set permissions as needed).
- Create a channel that the bot can use to send the "Create a ticket" embed.
- Create a bot application at the [discord developer panel](https://discord.com/developers/applications) and enable all intents. 
- Add the bot to your discord server by generating a OAuth2 invite link for your application and make sure to enable **bot** and **apps.commands**. Then for the permissions, tick Administrator.
- Create an empty PostgreSQL database for the bot, along with a user that can create tables in it.
- Create a `.env` file in the bot's folder and fill in every variable listed under [Configuration](#configuration) below — they are all required. See the example below:
  ```
  BOT_TOKEN=your-token-here
  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ticketbot
  ```
  The `postgresql+asyncpg://` prefix is required — that is what selects the async driver.
- Install dependencies with `uv sync`.
- Create the database tables with `uv run alembic upgrade head`. Run this again after pulling any update that changes the schema.
- **Upgrading from a version that used SQLite?** Import your old tickets once with `uv run python scripts/migrate_sqlite_to_postgres.py path/to/tickets.db`. It is safe to re-run; tickets already in PostgreSQL are skipped.
- Start the bot with `uv run ticketbot`. The bot will be fully running once the "Bot is up and running" message is outputted to the console.
- Run the **/sync** command in order to sync the bot's slash commands with discord.
- On first run the bot posts the "Create a ticket" embed and saves its message ID to the database automatically. **No restart is required** — earlier versions wrote that ID back into the config file and restarted themselves; that no longer happens.

---
### Configuration
Settings are split in two, by whether they can safely change while the bot is running.

**`.env` — read once at startup, restart to change.** Only the values the bot needs before it can reach the database, or that it cannot change without a restart anyway. This is the complete list, and all of them are required:

| variable | what it is |
| --- | --- |
| `BOT_TOKEN` | Your bot's token, from the Discord developer panel |
| `DATABASE_URL` | PostgreSQL connection string (must use the `postgresql+asyncpg://` prefix) |
| `GUILD_ID` | The server the bot runs in |
| `TICKET_LOGS_CHANNEL_ID` | Where system logs are sent |
| `TICKET_TRANSCRIPT_CHANNEL_ID` | Where ticket transcripts are sent |
| `DEBUG_LOG_SEND_ID` | The bot owner, who receives debug information |
| `ID_OF_CHANNEL_TO_SEND_TICKET_CREATION_EMBED` | Where the "Create a ticket" embed lives |
| `ACTIVE_TICKETS_CATEGORY_ID` | Category for active tickets |
| `ON_HOLD_TICKETS_CATEGORY_ID` | Category for on-hold tickets |
| `ARCHIVED_TICKETS_CATEGORY_ID` | Category for archived tickets |

**PostgreSQL — live, changed with `/config`, no restart.** Everything else: ticket types, the roles that staff each type, and the appearance/behavior settings. Nothing below is set in `.env`.

**Upgrading?** If your `.env` still carries settings that have since moved to the database (`EMBED_COLOR`, `FOOTER_OF_EMBEDS`, `BOT_STATUS_TYPE`, `BOT_STATUS_MESSAGE`, `MULTIPLE_TICKETS_ALLOWED`, `DM_TICKET_COPIES`, `TICKET_TYPE_ALLOWED_TO_CREATE_PRIVATE_CHANNELS`, `OPTIONS_DICT`, `CHANNEL_PERMS`, `ID_OF_MESSAGE_FOR_TICKET_CREATION`), they are read **once**, on the first start against an empty database, so your existing setup carries over untouched. After that they are ignored and can be deleted. Leaving them in place is harmless — unrecognised keys no longer cause a startup error.

| command | what it does |
| --- | --- |
| `/config show` | Show everything currently live |
| `/config types list` | List the ticket types in the creation dropdown |
| `/config types add <key> <label> <description> [position]` | Add a ticket type |
| `/config types edit <key> [label] [description] [position]` | Change a ticket type |
| `/config types remove <key> [force]` | Remove a ticket type |
| `/config roles list` | Show which roles staff each type |
| `/config roles add <type> <role>` | Give a role access to a ticket type |
| `/config roles remove <type> <role>` | Take that access away |
| `/config set <setting> <value>` | Change one setting (embed colour, footer, status, ticket limits, DM copies) |

Only the bot owner (`DEBUG_LOG_SEND_ID`) and server administrators can use these commands.

A few notes on the limits Discord imposes, which the commands enforce for you:
- At most **25 ticket types**, because that is the maximum number of options in a dropdown.
- Type labels and descriptions are capped at **100 characters**.
- Removing a type that still has open tickets is refused unless you pass `force: True`. Those tickets keep working afterwards, but staff role permissions no longer apply to them.

---
### Support
- Please open up a issue to report any bugs with the TicketBot.

---
### Known Errors
- Interaction fail on unknown slash command. (There is no error handling in the API for this yet, therefore a interaction fail will occur on the users side and a compiler error will be outputted to the console)
- Viewing Transcribed Tickets in a Web Browser, discord has restricted the ability to view sent files in a channel in a web browser. I am currently working on a fix to resolve this issue.
---
### Creators Note
- This bot is protected and licensed under the GNU General Public License v3.0. I am not liable for any damage that my bots may cause to your computer or discord server. I have the right to deny support for my bots at anytime for any reason. Even though this bot is open-sourced, it's source-code may be used for inspiration but may not be used for malicious intent or commercial use.  

- This is the fourth iteration of this bot, all previous versions have been used in private closed environments and will not be released to the public. This is the first public version of this bot.

- I would like to say a huge thanks to my good friend [Reb](https://rebsdesigns.com/). Without him, this whole idea of me making a "Ticket Bot" for discord would of never been possible. Thank you for giving me the opportunity to make a bot for you in the first place, kickstarting my devving career.

- Thank you to my good friend [Jake](https://github.com/jfmcdavitt) who helped me setup some of the backend parts of the bot. Without him, I would still be pondering on how am I going to make some parts of this thing work.