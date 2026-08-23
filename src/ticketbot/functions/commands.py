import sys
import discord
from datetime import UTC, datetime
from discord.utils import get
from ticketbot.utils.runtime_config import settings
from ticketbot.bot import bot, ticket
from ticketbot.models import TicketStatus
from ticketbot.utils.database import TicketRepository, health as database_health
from ticketbot.functions.create import embedButtons
from ticketbot.functions.options import optionsMenu
from ticketbot.utils.helpers import format_created_at, get_project_version, overall_status
from ticketbot.utils.updates import check_for_updates as check_github_for_updates

@ticket.command(name = "sync", description="Sync my command tree to Discord")
async def sync_command(interaction: discord.Interaction):
    author = interaction.user
    if author.id == settings.debug_log_send_id:
        embed1 = discord.Embed(description=f'Syncing Commands to Discord...', color=settings.embed_color)
        embed1.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed1.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        await interaction.response.send_message(embed=embed1, ephemeral=True)
        try:
            await ticket.sync()
            embed2 = discord.Embed(description=f'Commands Synced...', color=settings.embed_color)
            embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            await interaction.edit_original_response(embed=embed2)
        except Exception as e:
            embed2 = discord.Embed(title="**__An Error Occured:__**", description=f'Error: {e}', color=settings.embed_color)
            embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            await interaction.edit_original_response(embed=embed2)
    else:
        pass

@ticket.command(name = "create", description="Create a private ticket channel for you")
async def create_command(interaction: discord.Interaction, reason: str = 'Unspecified'):
    try:
        author = interaction.user
        guild = interaction.guild
        allowedAcess = False
        try:
            for allowedRoles in list(settings.channel_perms[f"{settings.ticket_type_allowed_to_create_private_channels}"]):
                prole = discord.utils.get(guild.roles, id=allowedRoles)
                if prole in author.roles:
                    allowedAcess = True
                else:
                    pass
        except TypeError:
            prole = get(guild.roles, id=settings.channel_perms[f"{settings.ticket_type_allowed_to_create_private_channels}"])
            if prole in author.roles:
                allowedAcess = True
            else:
                pass
        syslogc = discord.utils.get(guild.channels, id=settings.ticket_logs_channel_id)
        if allowedAcess == True:
            categoryn = settings.active_tickets_category_id
            category = discord.utils.get(guild.categories, id=categoryn)
            overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            prole: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            nchannel = await guild.create_text_channel(f'private-{author.display_name}', category=category, overwrites=overwrites, topic=f'Reason: {reason} | Created by: {author}')
            embed3 = discord.Embed(description=f'Private Ticket Channel created: {nchannel.mention}', color=settings.embed_color)
            embed3.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed3.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.send_message(embed=embed3, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'Private Ticket Channel created: {nchannel.mention}. A member of our team will be with you shortly.', ephemeral=True)
            embed1 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new private ticket', color=settings.embed_color)
            embed1.add_field(name=f'Reason:', value=f'{reason}')
            try:
                embed1.set_thumbnail(url=f'{author.display_avatar}')
            except Exception:
                pass
            embed1.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=bot.user.display_avatar)
            message10 = await nchannel.send(author.mention)
            await message10.delete()
            try:
                message3 = await nchannel.send(embed=embed1, view=embedButtons())
            except discord.HTTPException:
                message3 = await nchannel.send(f"Ticket Created by {author}, Reason: {reason}", view=embedButtons())
            await message3.pin()
            now = datetime.now(UTC)
            await TicketRepository.add(nchannel.id, author.id, now, settings.ticket_type_allowed_to_create_private_channels, TicketStatus.ACTIVE, message3.id)
            embed2 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new ticket', color=settings.embed_color)
            embed2.add_field(name='Channel:', value=f'{nchannel.mention}', inline=False)
            embed2.add_field(name=f'Reason:', value=f'{reason}', inline=False)
            embed2.add_field(name='Type:', value='Private', inline=False)
            embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await syslogc.send(embed=embed2)
            except discord.HTTPException:
                await syslogc.send(f"Ticket Created by {author}, Reason: {reason}")
        else:
            embed5 = discord.Embed(description=f'''{author.mention}, you can't use that command! ❌''', color=settings.embed_color)
            embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed5.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
            try:
                await interaction.response.send_message(embed=embed5, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''{author.mention}, **you can't use that command! ❌**''', ephemeral=True)    
    except Exception as e:
        await interaction.response.send_message('A unknown error has occurred, a copy of the error has been sent to the bot owner ❌', ephemeral=True)
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.dnd, activity=activity1)
        web = bot.get_user(settings.debug_log_send_id)
        text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
        embed = discord.Embed(title='commands.options function fail', description=f'{text}, {str(e)}', color=settings.embed_color)
        try:
            await web.send(embed=embed)
        except discord.HTTPException:
            await web.send("commands.options function fail" + str(e))
        print(text) 

@ticket.command(name = "options", description="Show you my options for this ticket channel")
async def options(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        author = interaction.user
        tchannel = interaction.channel
        roleList = []
        permissionGranted = False
        for roleids in settings.channel_perms.values():
            roleList.extend(roleids)
        for allowedRoles in roleList:
            arole = get(guild.roles, id=allowedRoles)
            if arole in author.roles:
                permissionGranted = True
            else:
                pass
        if permissionGranted == True:
            ticketInfo = await TicketRepository.find(tchannel.id)
            if ticketInfo != None:
                acategory = discord.utils.get(guild.categories, id=settings.archived_tickets_category_id)
                acategoryc = (50 - (len(acategory.channels)))
                if acategoryc == 0:
                    acategoryc2 = str(f'{acategoryc} slots left (full)')
                elif acategoryc == 1:
                    acategoryc2 = str(f'{acategoryc} slot left (almost full)')
                elif acategoryc <= 5:
                    acategoryc2 = str(f'{acategoryc} slots left (almost full)')
                elif acategoryc >= 6:
                    acategoryc2 = str(f'{acategoryc} slots left')
                text = str(f'''🚩- Claim a ticket\n\n👥- Add a member to the ticket\n\n👋- Remove a member from the ticket\n\n🟢- Mark a ticket as active\n\n✋- Mark a ticket as onhold\n\n📓- Rename a ticket channel\n\n🗄️- Place a ticket in the archives **({acategoryc2})**\n\n📝- Transcribe and delete a ticket                        ''')
                embed3 = discord.Embed(title='''**Ticket Options**''', description=f'{text}', color=settings.embed_color)
                lauthor4 = get(guild.members, id=ticketInfo.author_id)
                if lauthor4 == None:
                    lauthor5 = await bot.fetch_user(ticketInfo.author_id)
                    if lauthor5 == None:
                        lauthor = str("N/A")
                    else:
                        lauthor = lauthor5
                else:
                    lauthor = lauthor4
                ltype = ticketInfo.type
                lcreation = format_created_at(ticketInfo.created_at)
                lstatus = ticketInfo.status.value.capitalize()
                if ticketInfo.claimed_by != None:
                    claimer = await bot.fetch_user(ticketInfo.claimed_by)
                    cstatus = str(f"**Claimed** ({claimer.mention})")
                else:
                    cstatus = str(f'**Not Claimed**')
                if lauthor == 'N/A':
                    text2 = str(f'''**__Author:__** N/A\n**__Type:__** {ltype}\n**__Status:__** {lstatus}\n**__Creation Date/Time:__** {lcreation}\n**__Claim Status:__** {cstatus}''')
                else:
                    text2 = str(f'''**__Author:__** {lauthor.mention}\n**__Type:__** {ltype}\n**__Status:__** {lstatus}\n**__Creation Date/Time:__** {lcreation}\n**__Claim Status:__** {cstatus}''')
                embed3.add_field(name="Ticket Infomation:", value=f"{text2}")
                embed3.set_author(name=f'{author}', icon_url=author.display_avatar)
                embed3.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                try:
                    await interaction.response.send_message(embed=embed3, ephemeral=True, view=optionsMenu())
                except discord.HTTPException:
                    await interaction.response.send_message("HTTP Error that I'm too lazy to type out. Try again.", ephemeral=True)
            else:
                embed5 = discord.Embed(description=f'''You can only use this command in a ticket channel!''', color=settings.embed_color)
                embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed5.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                try:
                    await interaction.response.send_message(embed=embed5, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''**You can only use this command in a ticket channel!****''')
        else:
            embed5 = discord.Embed(description=f'''You can't use that command!''', color=settings.embed_color)
            embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed5.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
            try:
                await interaction.response.send_message(embed=embed5, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''**You can't use that command!****''')
    except Exception as e:
        await interaction.response.send_message('A unknown error has occurred, a copy of the error has been sent to the bot owner ❌', ephemeral=True)
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.dnd, activity=activity1)
        web = bot.get_user(settings.debug_log_send_id)
        text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
        embed = discord.Embed(title='commands.options function fail', description=f'{text}, {str(e)}', color=settings.embed_color)
        try:
            await web.send(embed=embed)
        except discord.HTTPException:
            await web.send("commands.options function fail" + str(e))
        print(text) 

 
@ticket.command(name = "info", description="Tell you about myself and how I'm doing")
async def info_command(interaction:discord.Interaction):
    author = interaction.user
    # The database probe and the GitHub lookup are real network calls and Discord only
    # allows three seconds for the initial response, so a loading embed goes out first
    # and is edited in place once the checks return -- the same pattern /sync uses.
    embedLoading = discord.Embed(title='Information', description='Running health checks...', color=settings.embed_color)
    embedLoading.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
    embedLoading.set_author(name=f'{author}', icon_url=author.display_avatar)
    await interaction.response.send_message(embed=embedLoading, ephemeral=True)
    try:
        version = get_project_version()
        embed6 = discord.Embed(title='Information', description=f'''Hi there! I'm **{bot.user.name}**, a discord ticket system bot designed by WebTheDev on GitHub!''', color=settings.embed_color)
        latency = bot.latency * 1000
        embed6.add_field(name="**__Latency__**", value=f"❤️: {latency:.2f}ms")
        botOwner = await bot.fetch_user(settings.debug_log_send_id)
        embed6.add_field(name="**__Bot Owner__**", value=f"{botOwner.mention}")
        embed6.add_field(name= "**__Version__**", value=f"`{version}`")
        embed6.add_field(name="**__Github Repository__**", value="[Click Me!](https://github.com/WebTheDev/TicketBot)")
        botCreator = await bot.fetch_user(387002430602346499)
        embed6.add_field(name="**__Bot Creator__**", value=f"{botCreator}")
        databaseHealth = await database_health()
        embed6.add_field(name="**__Database__**", value=databaseHealth.describe())
        updateStatus = await check_github_for_updates(version)
        embed6.add_field(name="**__Updates__**", value=updateStatus.describe())
        embed6.add_field(name="**__Status__**", value=overall_status(databaseHealth, latency))
        embed6.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        embed6.set_author(name=f'{author}', icon_url=author.display_avatar)
        try:
            await interaction.edit_original_response(embed=embed6)
        except discord.HTTPException:
            await interaction.edit_original_response(content="Something funny happened here, try again", embed=None)
    except Exception as e:
        await interaction.edit_original_response(content='A unknown error has occurred, a copy of the error has been sent to the bot owner ❌', embed=None)
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.dnd, activity=activity1)
        web = bot.get_user(settings.debug_log_send_id)
        text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
        embed = discord.Embed(title='commands.options function fail', description=f'{text}, {str(e)}', color=settings.embed_color)
        try:
            await web.send(embed=embed)
        except discord.HTTPException:
            await web.send("commands.options function fail" + str(e))
        print(text)


@ticket.command(name = "python", description="Ask me not to do it")
async def python_command(interaction:discord.Interaction):
    try:
        author = interaction.user
        embed = discord.Embed(description=f"DON'T DO IT **{author.display_name}**!!", color=settings.embed_color)
        embed.set_image(url="https://static2.klipy.com/ii/9294a2e836d178ddc22430dd7765727e/90/26/wFRb90uxMElMZVQF1o1.gif")
        embed.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.avatar}')
        embed.set_author(name=f'{author}', icon_url=author.avatar)
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("https://static2.klipy.com/ii/9294a2e836d178ddc22430dd7765727e/90/26/wFRb90uxMElMZVQF1o1.gif", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message('A unknown error has occurred, a copy of the error has been sent to the bot owner ❌', ephemeral=True)
        activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
        await bot.change_presence(status=discord.Status.dnd, activity=activity1)
        web = bot.get_user(settings.debug_log_send_id)
        text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
        embed = discord.Embed(title='commands.python function fail', description=f'{text}, {str(e)}', color=settings.embed_color)
        try:
            await web.send(embed=embed)
        except discord.HTTPException:
            await web.send("commands.python function fail" + str(e))
        print(text) 