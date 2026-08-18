import discord, datetime
import sys
import os
from datetime import datetime
from discord.utils import get
from config import settings, update_env
from utils.database import *
from bot import bot, ticket
from functions.options import *
from functions.create import *
import functions.commands  # noqa: F401 -- registers /sync, /create, /options, /info, /python

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    databasecon = TicketData.connect()
    databasecur = TicketData.cursor(databasecon)
    if TicketData.verifylayout(databasecur) == True:
        print ("------------------------------------")
        print("[MESSAGE]: Ticket Database found.")
    else:
        print ("------------------------------------------------------")
        print("[WARN]: Ticket Database not found. Creating Database...")
        TicketData.createlayout(databasecon, databasecur)
    print ("------------------------------------")
    print (f"Bot Name: {bot.user.name}#{bot.user.discriminator}")
    print (f"Bot ID: {bot.user.id}")
    print ("Discord Version: " + discord.__version__)
    print ("------------------------------------")
    if f'{settings.bot_status_type}' == 'Playing':
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.online, activity=activity1)
    elif f'{settings.bot_status_type}' == 'Streaming':
        activity1 = discord.Activity(type=discord.ActivityType.streaming, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.online, activity=activity1)
    elif f'{settings.bot_status_type}' == 'Watching':
        activity1 = discord.Activity(type=discord.ActivityType.watching, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.online, activity=activity1)
    elif f'{settings.bot_status_type}' == 'Listening':
        activity1 = discord.Activity(type=discord.ActivityType.listening, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.online, activity=activity1)
    else:
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.online, activity=activity1)
        print('''[WARN]: You have incorrectly specified the bot's activity type, the default has been selected. ''')
        print("----------------------------------------------------")
    if settings.first_run == True:
        print("[MESSAGE]: First Run is set to true, syncing slash commands with discord and generating ticket creation embed...")
        print("--------------------------------------------------------------------------------")
        await ticket.sync()
        tchannel = bot.get_channel(settings.id_of_channel_to_send_ticket_creation_embed)
        embed = discord.Embed(title='''**Create a ticket**''', description=f'Press the button below to create a ticket!', color=settings.embed_color)
        embed.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        nmessage = await tchannel.send(embed=embed, view=TicketCreation())
        update_env(id_of_message_for_ticket_creation=nmessage.id, first_run=False)
        embed2 = discord.Embed(title='**__Embed Message ID Updated:__**', description=f'New Message ID is: `{nmessage.id}`\n **Please restart the bot if not restarted automatically**', color=settings.embed_color)
        embed2.set_footer(text=f'{bot.user.name} | {bot.user.id}', icon_url=f'{bot.user.display_avatar}')
        developer = bot.get_user(settings.debug_log_send_id)
        try:
            await developer.send(embed=embed2)
        except discord.HTTPException:
            await developer.send(f"**__Embed Message ID Updated:__**\nNew Message ID is: `{nmessage.id}`\n **Please restart the bot if not restarted automatically**")
        await bot.close()
        print("[WARN]: Embed Message Generated! Please restart the bot if not restarted automatically.")
        print("--------------------------------------------------------------------------------")
        os.execv(sys.argv[0], sys.argv)
    else:
        allTickets = []
        allTickets = TicketData.getall(databasecur, allTickets)
        for tickets in allTickets:
            channelID = int(tickets[0])
            messageID = int(tickets[6])
            tchannel = bot.get_channel(channelID)
            if tchannel != None:
                tmessage = await tchannel.fetch_message(messageID)
                await tmessage.edit(view=embedButtons(timeout=None))
            else:
                pass
        embed = discord.Embed(title='''**Create a ticket**''', description=f'Press the button below to create a ticket!', color=settings.embed_color)
        embed.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            tchannel = bot.get_channel(settings.id_of_channel_to_send_ticket_creation_embed)
            tmessage = await tchannel.fetch_message(settings.id_of_message_for_ticket_creation)
            await tmessage.edit(embed=embed, view=TicketCreation(timeout=None))
            print("[MESSAGE]: Relinked to Ticket Creation Embed, standing by for ticket creation...")
            print("---------------------------------------------------------------------------------")
        except Exception:
                print("[ERROR]: Embed Message not found! Creating a new embed message, please restart the bot if not restarted automatically")
                print("--------------------------------------------------------------------------------")
                nmessage = await tchannel.send(embed=embed, view=TicketCreation())
                update_env(id_of_message_for_ticket_creation=nmessage.id)
                embed2 = discord.Embed(title='**__Embed Message ID Updated:__**', description=f'New Message ID is: `{nmessage.id}`\n **Please restart the bot if not restarted automatically**', color=settings.embed_color)
                embed2.set_footer(text=f'{bot.user.name} | {bot.user.id}', icon_url=f'{bot.user.display_avatar}')
                developer = bot.get_user(settings.debug_log_send_id)
                try:
                    await developer.send(embed=embed2)
                except discord.HTTPException:
                    await developer.send(f"**__Embed Message ID Updated:__**\nNew Message ID is: `{nmessage.id}`\n **Please restart the bot if not restarted automatically**")
                await bot.close()
                os.execv(sys.argv[0], sys.argv)
    print("[MESSAGE]: Bot is up and running!")
    print("------------------------------------")
    TicketData.close(databasecon)


def main():
    try:
        bot.run(settings.bot_token)
    except discord.errors.LoginFailure as e:
        print('Login Failed, ERROR 401 Unauthorized')

if __name__ == "__main__":
    main()