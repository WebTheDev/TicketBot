import discord
import sys
from datetime import UTC, datetime
from discord.utils import get
from ticketbot.utils.runtime_config import settings
from ticketbot.models import TicketStatus
from ticketbot.utils.database import TicketRepository
from ticketbot.utils.helpers import format_created_at
from ticketbot.bot import bot
from ticketbot.functions.options import optionsMenu, yesOrNoOption

class TicketCreationMenu(discord.ui.Select):

    def __init__(self):
        def optionsList():
            # Read from the runtime cache rather than the database: this runs in a
            # synchronous constructor and cannot await. The cache is refreshed at startup
            # and after every /config write, so a type added a moment ago is already here.
            oList = []
            for ticketType in settings.ticket_types:
                oList.append(discord.SelectOption(label=ticketType.label, value=ticketType.key, description=ticketType.description))
            return oList
        super().__init__(placeholder="Select an option...", options=optionsList(), min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        author = interaction.user
        x[interaction.user.display_name] = f"{self.values[0]}"
        await interaction.response.send_modal(TicketCreationModal())
        embed2 = discord.Embed(description=f'You can only select an option once!', color=settings.embed_color)
        embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
        await interaction.edit_original_response(embed=embed2, view=None)


class TicketCreationMenuUI(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketCreationMenu())

class embedButtons(discord.ui.View):
    @discord.ui.button(label="Close Ticket", emoji="📝", style=discord.ButtonStyle.red)
    async def closeTicket(self, interaction: discord.Interaction, button: discord.Button):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        ticketInfo = await TicketRepository.find(tchannel.id)
        if ticketInfo == None:
            embed7 = discord.Embed(description=f'''This channel isn't a tracked ticket, so there is nothing to close.''', color=settings.embed_color)
            embed7.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed7.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.send_message(embed=embed7, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f"**This channel isn't a tracked ticket, so there is nothing to close.**", ephemeral=True)
            return
        ltype = ticketInfo.type
        allowedAccess = False
        try:
            for allowedRoles in list(settings.channel_perms[f"{ltype}"]):
                prole = discord.utils.get(guild.roles, id=allowedRoles)
                if prole in author.roles:
                    allowedAccess = True
                else:
                    pass
        except TypeError:
            prole = get(guild.roles, id=settings.channel_perms[f"{ltype}"])
            if prole in author.roles:
                allowedAccess = True
            else:
                pass
        if (allowedAccess == True) or (ticketInfo.author_id == author.id):
            embed6 = discord.Embed(description="Are you sure that you want to close this ticket? This will result in the ticket being deleted.", color=settings.embed_color)
            embed6.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed6.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.send_message(embed=embed6, view=yesOrNoOption(timeout=None), ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message("Something weird happened here, try again.")
        else:
            embed5 = discord.Embed(description=f'''Only the author of the ticket can use this button!''', color=settings.embed_color)
            embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed5.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
            try:
                await interaction.response.send_message(embed=embed5, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''**You can't use that command!****''')

    @discord.ui.button(label="Options", emoji="⚙️", style=discord.ButtonStyle.green)
    async def ticketOptions(self, interaction: discord.Interaction, button: discord.Button):
        try:
            guild = interaction.guild
            author = interaction.user
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
            tchannel = interaction.channel
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
            await interaction.response.send_message('A unknown error has occurred, a copy of the error has been sent to the developer ❌', ephemeral=True)
            activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{settings.bot_status_message}')
            await bot.change_presence(status=discord.Status.dnd, activity=activity1)
            web = bot.get_user(settings.debug_log_send_id)
            text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
            embed = discord.Embed(title='commands.options function fail', description=f'{text}, {str(e)}', color=settings.embed_color)
            try:
                await web.send(embed=embed)
            except discord.HTTPException:
                await web.send("commands.options function fail" + str(e))
            print(str(e))

class TicketCreationModal(discord.ui.Modal, title=f"Create a ticket"):
    answer = discord.ui.TextInput(label='Please provide a brief Ticket Description...', style=discord.TextStyle.paragraph, required=True, max_length=128)

    async def on_submit(self, interaction: discord.Interaction):
        ticketType = (x.get(interaction.user.display_name))
        author = interaction.user
        ticketDescription = (self.children[0].value)
        guild = bot.get_guild(settings.guild_id)
        me = bot.get_user(bot.user.id)
        default_perms = {}
        default_perms[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
        default_perms[me] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        default_perms[author] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            for allowedRoles in list(settings.channel_perms[f"{ticketType}"]):
                prole = get(guild.roles, id=allowedRoles)
                default_perms[prole] = discord.PermissionOverwrite(read_messages=True, send_messages=True)       
        except TypeError:
            prole = get(guild.roles, id=settings.channel_perms[f"{ticketType}"])
            default_perms[prole] = discord.PermissionOverwrite(read_messages=True, send_messages=True)  
        now = datetime.now(UTC)
        category = discord.utils.get(guild.categories, id=settings.active_tickets_category_id)
        tchannel = await guild.create_text_channel(name=f'{ticketType}-{author.display_name}', category=category, overwrites=default_perms, topic=f"Reason: {ticketDescription} | Created by: {author}")
        embed3 = discord.Embed(description=f'Your {ticketType} ticket has been created, {tchannel.mention}. A member of our team will be with you shortly.', color=settings.embed_color)
        embed3.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed3.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.send_message(embed=embed3, ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message(f'Your {ticketType} ticket has been created, {tchannel.mention}. A member of our team will be with you shortly.', ephemeral=True)
        messageString = ""
        try:
            for rolesToPing in list(settings.channel_perms[f"{ticketType}"]):
                prole = get(guild.roles, id=rolesToPing)
                messageString = messageString + (f" {prole.mention}")
            await tchannel.send(messageString)
        except TypeError:
            prole = get(guild.roles, id=settings.channel_perms[ticketType])
            await tchannel.send(f'{prole.mention}')
        embed1 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new {ticketType} ticket', color=settings.embed_color)
        embed1.add_field(name=f'Reason:', value=f'{ticketDescription}')
        try:
            embed1.set_thumbnail(url=f'{author.display_avatar}')
        except Exception:
            pass
        embed1.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=bot.user.display_avatar)
        try:
            message2 = await tchannel.send(embed=embed1, view=embedButtons(timeout=None))
        except discord.HTTPException:
            message2 = await tchannel.send(f"Ticket Created by {author}, Reason: {ticketDescription}", view=embedButtons(timeout=None))
        await message2.pin()
        await TicketRepository.add(tchannel.id, author.id, now, ticketType, TicketStatus.ACTIVE, message2.id)
        embed2 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new ticket', color=settings.embed_color)
        embed2.add_field(name='Channel:', value=f'{tchannel.mention}', inline=False)
        embed2.add_field(name=f'Reason:', value=f'{ticketDescription}', inline=False)
        embed2.add_field(name='Type:', value=f'{ticketType}', inline=False)
        embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=bot.user.display_avatar)
        syslogc = await bot.fetch_channel(settings.ticket_logs_channel_id)
        try:
            await syslogc.send(embed=embed2)
        except discord.HTTPException:
            await syslogc.send(f"Ticket Created by {author}, Reason: {ticketDescription}")
        del x[interaction.user.display_name]

class TicketCreation(discord.ui.View):
    @discord.ui.button(label="Create a new ticket", emoji="📩", style=discord.ButtonStyle.blurple)
    async def presscreate(self, interaction:discord.Interaction, button:discord.ui.button):
        author = interaction.user
        guild = interaction.guild
        if settings.multiple_tickets_allowed == False:
            openTicket = await TicketRepository.find_open_ticket_for(
                author.id, settings.ticket_type_allowed_to_create_private_channels
            )
            if openTicket != None:
                achannel = get(guild.channels, id=openTicket.channel_id)
                embed2 = discord.Embed(description=f"You can't have more than one ticket open at a time! Please close your current ticket before opening a new one.", color=settings.embed_color)
                embed2.add_field(name="**__Open Tickets:__**", value=f"{achannel.mention}")
                embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                await interaction.response.send_message(embed=embed2, ephemeral=True)
            else:
                embed2 = discord.Embed(description=f'Hi there {author.name}! Please select a ticket option from the drop-down list below!', color=settings.embed_color)
                embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                await interaction.response.send_message(embed=embed2, view=TicketCreationMenuUI(), ephemeral=True)
        else:
            embed2 = discord.Embed(description=f'Hi there {author.name}! Please select a ticket option from the drop-down list below!', color=settings.embed_color)
            embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed2.set_footer(text=f"{settings.footer_of_embeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
            await interaction.response.send_message(embed=embed2, view=TicketCreationMenuUI(), ephemeral=True)
    
x = dict() 