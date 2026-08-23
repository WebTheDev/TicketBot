import discord
import asyncio
from ticketbot.utils.runtime_config import settings
from ticketbot.utils.database import TicketRepository, dispose, schema_ready
from ticketbot.utils.helpers import apply_presence, build_creation_embed, is_creation_embed
from ticketbot.bot import bot, ticket
from ticketbot.functions.create import TicketCreation, embedButtons
import ticketbot.functions.commands  # noqa: F401 # pyright: ignore[reportUnusedImport] -- registers /sync, /create, /options, /info, /python
import ticketbot.functions.config_commands  # noqa: F401 # pyright: ignore[reportUnusedImport] -- registers the /config group

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    if await schema_ready() == True:
        print ("------------------------------------")
        print("[MESSAGE]: Ticket Database found.")
    else:
        print ("--------------------------------------------------------------------------------")
        print("[ERROR]: Ticket Database not reachable, or its tables do not exist.")
        print("[ERROR]: Check DATABASE_URL in .env, then run: uv run alembic upgrade head")
        print("--------------------------------------------------------------------------------")
        await bot.close()
        return
    # Load the live config before anything reads a setting; every settings.* lookup from
    # here on is served from this cache.
    seeded = await settings.bootstrap()
    if seeded:
        print ("--------------------------------------------------------------------------------")
        print(f"[MESSAGE]: Seeded the live config from .env: {', '.join(seeded)}.")
        print("[MESSAGE]: These settings now live in PostgreSQL and are managed with /config.")
        print("[MESSAGE]: The legacy keys can be removed from .env; they are no longer read.")
        print("--------------------------------------------------------------------------------")
    if not settings.ticket_types:
        print("[WARN]: No ticket types are configured, so the creation dropdown will be empty.")
        print("[WARN]: Add one with: /config types add")
    print ("------------------------------------")
    print (f"Bot Name: {bot.user.name}#{bot.user.discriminator}")
    print (f"Bot ID: {bot.user.id}")
    print ("Discord Version: " + discord.__version__)
    print ("------------------------------------")
    # Shared with /config set, so a status change applies without a restart.
    if await apply_presence(bot, settings.bot_status_type, settings.bot_status_message) == False:
        print('''[WARN]: You have incorrectly specified the bot's activity type, the default has been selected. ''')
        print("----------------------------------------------------")
    # A missing creation_message_id is what "first run" means now -- there is no flag to
    # keep in sync, and persisting the new ID to PostgreSQL takes effect immediately, so
    # the bot no longer has to restart itself to pick it up.
    if settings.creation_message_id == None:
        print("[MESSAGE]: No ticket creation embed on record, syncing slash commands...")
        print("--------------------------------------------------------------------------------")
        await ticket.sync()
        await establish_creation_embed()
    else:
        allTickets = await TicketRepository.all_tickets()
        for tickets in allTickets:
            tchannel = bot.get_channel(tickets.channel_id)
            if tchannel != None:
                tmessage = await tchannel.fetch_message(tickets.message_id)
                await tmessage.edit(view=embedButtons(timeout=None))
            else:
                pass
        tchannel = creation_channel()
        if tchannel == None:
            print("[WARN]: I can't see the channel I post the ticket creation embed in.")
            print("[WARN]: Check ID_OF_CHANNEL_TO_SEND_TICKET_CREATION_EMBED in .env and my permissions.")
            print("--------------------------------------------------------------------------------")
        else:
            try:
                tmessage = await tchannel.fetch_message(settings.creation_message_id)
            except discord.NotFound:
                # Genuinely deleted, so the recorded ID is dead and a replacement is safe.
                print("[WARN]: The recorded ticket creation embed no longer exists.")
                print("--------------------------------------------------------------------------------")
                await establish_creation_embed()
            except discord.HTTPException as error:
                # A rate limit or outage is temporary. Posting a replacement here would
                # orphan a message that is still perfectly alive, so leave it alone.
                print(f"[WARN]: Couldn't reach the ticket creation embed ({error}).")
                print("[WARN]: Leaving it on record; its button will relink on the next restart.")
                print("--------------------------------------------------------------------------------")
            else:
                await tmessage.edit(embed=creation_embed(), view=TicketCreation(timeout=None))
                print("[MESSAGE]: Relinked to Ticket Creation Embed, standing by for ticket creation...")
                print("---------------------------------------------------------------------------------")
    print("[MESSAGE]: Bot is up and running!")
    print("------------------------------------")


CREATION_EMBED_SEARCH_LIMIT = 200


def creation_channel():
    return bot.get_channel(settings.id_of_channel_to_send_ticket_creation_embed)


def creation_embed() -> discord.Embed:
    return build_creation_embed(bot, settings.embed_color, settings.footer_of_embeds)


async def find_existing_creation_embed(channel):
    """Look for a creation embed this bot already posted in `channel`.

    Without this, an operator who already has a creation embed -- from a previous
    install, or a database that was reset -- gets a second one posted the moment the bot
    starts, because there is no chance to run /config creation-message beforehand.
    """
    try:
        async for message in channel.history(limit=CREATION_EMBED_SEARCH_LIMIT):
            if is_creation_embed(message, bot.user.id):
                return message
    except discord.HTTPException as error:
        print(f"[WARN]: Couldn't read {channel} to look for an existing creation embed ({error}).")
    return None


async def establish_creation_embed():
    """Adopt an existing creation embed if there is one, otherwise post a fresh one."""
    channel = creation_channel()
    if channel == None:
        print("[ERROR]: I can't see the channel I'm meant to post the ticket creation embed in.")
        print("[ERROR]: Check ID_OF_CHANNEL_TO_SEND_TICKET_CREATION_EMBED in .env and my permissions.")
        print("--------------------------------------------------------------------------------")
        return
    existing = await find_existing_creation_embed(channel)
    if existing != None:
        await existing.edit(embed=creation_embed(), view=TicketCreation(timeout=None))
        await settings.set_value("creation_message_id", existing.id)
        print(f"[MESSAGE]: Found an existing ticket creation embed (message ID {existing.id}) and adopted it.")
        print("[MESSAGE]: No duplicate was posted; the ID is now saved in the database.")
        print("--------------------------------------------------------------------------------")
        return
    if settings.auto_post_creation_embed == False:
        print("[WARN]: No ticket creation embed on record and auto-posting is turned off.")
        print("[WARN]: Point me at your existing message with: /ticket config creation-message")
        print("--------------------------------------------------------------------------------")
        return
    await post_creation_embed()


async def post_creation_embed():
    """Post the "Create a ticket" embed and record its ID in PostgreSQL.

    Used both on first run and when the recorded message has gone missing. The ID is
    saved to the database and the cache is refreshed in place, so the bot keeps running
    -- this is what used to require bot.close() plus os.execv to reload from .env.
    """
    tchannel = creation_channel()
    nmessage = await tchannel.send(embed=creation_embed(), view=TicketCreation(timeout=None))
    await settings.set_value("creation_message_id", nmessage.id)
    print(f"[MESSAGE]: Ticket creation embed posted and saved (message ID {nmessage.id}). No restart needed.")
    print("--------------------------------------------------------------------------------")
    developer = bot.get_user(settings.debug_log_send_id)
    if developer == None:
        return
    embed2 = discord.Embed(title='**__Ticket Creation Embed Posted:__**', description=f'New Message ID is: `{nmessage.id}`\nIt has been saved to the database; no restart is required.', color=settings.embed_color)
    embed2.set_footer(text=f'{bot.user.name} | {bot.user.id}', icon_url=f'{bot.user.display_avatar}')
    try:
        await developer.send(embed=embed2)
    except discord.HTTPException:
        await developer.send(f"**__Ticket Creation Embed Posted:__**\nNew Message ID is: `{nmessage.id}`\nIt has been saved to the database; no restart is required.")


async def run_bot():
    discord.utils.setup_logging()
    try:
        async with bot:
            await bot.start(settings.bot_token)
    finally:
        await dispose()

def main():
    try:
        asyncio.run(run_bot())
    except discord.errors.LoginFailure:
        print('Login Failed, ERROR 401 Unauthorized')