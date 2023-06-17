import discord
import asyncio
import sys
from datetime import datetime
from discord.utils import get
from config import *
from database import *
from bot import * 
from options import *

class TicketCreationMenu(discord.ui.Select):

    def __init__(self):
        def optionsList():
            listofOptions = list(OptionsDict.values())
            oList = []
            for presets in listofOptions:
                oList.append(discord.SelectOption(label=presets[0], value=presets[1], description=presets[2]))
            return oList
        super().__init__(placeholder="Select an option...", options=optionsList(), min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        author = interaction.user
        x[interaction.user.display_name] = f"{self.values[0]}"
        await interaction.response.send_modal(TicketCreationModal())
        embed2 = discord.Embed(description=f'You can only select an option once!', color=embedColor)
        embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
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
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        TicketData.close(connection)
        ltype = (ticketInfo[4])
        allowedAccess = False
        try:
            for allowedRoles in list(channelPerms[f"{ltype}"]):
                prole = discord.utils.get(guild.roles, id=allowedRoles)
                if prole in author.roles:
                    allowedAccess = True
                else:
                    pass
        except TypeError:
            prole = get(guild.roles, id=channelPerms[f"{ltype}"])
            if prole in author.roles:
                allowedAccess = True
            else:
                pass
        if (allowedAccess == True) or (f"{ticketInfo[1]}" == f"{author.id}"):
            embed6 = discord.Embed(description="Are you sure that you want to close this ticket? This will result in the ticket being deleted.", color=embedColor)
            embed6.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed6.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.send_message(embed=embed6, view=yesOrNoOption(timeout=None), ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message("Something weird happened here, try again.")
        else:
            embed5 = discord.Embed(description=f'''Only the author of the ticket can use this button!''', color=embedColor)
            embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed5.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
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
            for roleids in channelPerms.values():
                roleList.append(roleids)
            for allowedRoles in roleList:
                arole = get(guild.roles, id=allowedRoles)
                if arole in author.roles:
                    permissionGranted = True
                else:
                    pass
            tchannel = interaction.channel
            if permissionGranted == True:
                connection = TicketData.connect()
                cursor = TicketData.cursor(connection)
                ticketInfo = TicketData.find(cursor, tchannel.id)
                TicketData.close(connection)
                if ticketInfo != None:
                    acategory = discord.utils.get(guild.categories, id=archivedTicketsCategoryID)
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
                    embed3 = discord.Embed(title='''**Ticket Options**''', description=f'{text}', color=embedColor)
                    try:
                        lauthor2 = (ticketInfo[1])
                        lauthor3 = (int(lauthor2))
                        lauthor4 = get(guild.members, id=lauthor3)
                        if lauthor4 == None:
                            lauthor5 = await bot.fetch_user(lauthor3)
                            if lauthor5 == None:
                                lauthor = str("N/A") 
                            else:
                                lauthor = lauthor5
                        else:
                            lauthor = lauthor4
                    except IndexError:
                        lauthor = str("N/A")
                    try:
                        ltype = (ticketInfo[4])
                    except IndexError:
                        ltype = str("N/A")
                    try:
                        lcreation = (ticketInfo[3])
                    except IndexError:
                        lcreation = str("N/A")
                    try:
                        lstatus = (ticketInfo[5])
                    except IndexError:
                        lstatus = str("N/A")
                    if (ticketInfo[2]) != "No":
                        lcstatus = (ticketInfo[2])
                        lcstatus2 = int(lcstatus)
                        claimer = await bot.fetch_user(lcstatus2)
                        cstatus = str(f"**Claimed** ({claimer.mention})")
                    else:
                        cstatus = str(f'**Not Claimed**')
                    if lauthor == 'N/A':
                        text2 = str(f'''**__Author:__** N/A\n**__Type:__** {ltype}\n**__Status:__** {lstatus}\n**__Creation Date/Time:__** {lcreation}\n**__Claim Status:__** {cstatus}''')
                    else:
                        text2 = str(f'''**__Author:__** {lauthor.mention}\n**__Type:__** {ltype}\n**__Status:__** {lstatus}\n**__Creation Date/Time:__** {lcreation}\n**__Claim Status:__** {cstatus}''')
                    embed3.add_field(name="Ticket Infomation:", value=f"{text2}")
                    embed3.set_author(name=f'{author}', icon_url=author.display_avatar)
                    embed3.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                    try:
                        await interaction.response.send_message(embed=embed3, ephemeral=True, view=optionsMenu())
                    except discord.HTTPException:
                        await interaction.response.send_message("HTTP Error that I'm too lazy to type out. Try again.", ephemeral=True)
                else:
                    embed5 = discord.Embed(description=f'''You can only use this command in a ticket channel!''', color=embedColor)
                    embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                    embed5.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                    try:
                        await interaction.response.send_message(embed=embed5, ephemeral=True)
                    except discord.HTTPException:
                        await interaction.response.send_message(f'''**You can only use this command in a ticket channel!****''')
            else:
                embed5 = discord.Embed(description=f'''You can't use that command!''', color=embedColor)
                embed5.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed5.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                try:
                    await interaction.response.send_message(embed=embed5, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''**You can't use that command!****''')
        except Exception as e:
            message2 = await interaction.response.send_message(f'A unknown error has occurred, a copy of the error has been sent to the developer ❌', ephemeral=True)
            activity1 = discord.Activity(type=discord.ActivityType.playing, name=f'{botStatusMessage}')
            await bot.change_presence(status=discord.Status.dnd, activity=activity1)
            web = bot.get_user(debugLogSendID)
            text = str('''Error on line {}'''.format(sys.exc_info()[-1].tb_lineno))
            embed = discord.Embed(title='commands.options function fail', description=f'{text}, {str(e)}', color=embedColor)
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
        guild = bot.get_guild(guildID)
        me = bot.get_user(bot.user.id)
        default_perms = {}
        default_perms[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
        default_perms[me] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        default_perms[author] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        try:
            for allowedRoles in list(channelPerms[f"{ticketType}"]):
                prole = get(guild.roles, id=allowedRoles)
                default_perms[prole] = discord.PermissionOverwrite(read_messages=True, send_messages=True)       
        except TypeError:
            prole = get(guild.roles, id=channelPerms[f"{ticketType}"])
            default_perms[prole] = discord.PermissionOverwrite(read_messages=True, send_messages=True)  
        now = datetime.now().strftime("%m-%d-%Y, %H:%M:%S")
        category = discord.utils.get(guild.categories, id=activeTicketsCategoryID)
        tchannel = await guild.create_text_channel(name=f'{ticketType}-{author}', category=category, overwrites=default_perms, topic=f"Reason: {ticketDescription} | Created by: {author}")
        embed3 = discord.Embed(description=f'Your {ticketType} ticket has been created, {tchannel.mention}. A member of our team will be with you shortly.', color=embedColor)
        embed3.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed3.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.send_message(embed=embed3, ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message(f'Your {ticketType} ticket has been created, {tchannel.mention}. A member of our team will be with you shortly.', ephemeral=True)
        messageString = ""
        try:
            for rolesToPing in list(channelPerms[f"{ticketType}"]):
                prole = get(guild.roles, id=rolesToPing)
                messageString = messageString + (f" {prole.mention}")
            await tchannel.send(messageString)
        except TypeError:
            prole = get(guild.roles, id=channelPerms[ticketType])
            await tchannel.send(f'{prole.mention}')
        embed1 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new {ticketType} ticket', color=embedColor)
        embed1.add_field(name=f'Reason:', value=f'{ticketDescription}')
        try:
            embed1.set_thumbnail(url=f'{author.display_avatar}')
        except Exception:
            pass
        embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=bot.user.display_avatar)
        try:
            message2 = await tchannel.send(embed=embed1, view=embedButtons(timeout=None))
        except discord.HTTPException as y:
            message2 = await tchannel.send(f"Ticket Created by {author}, Reason: {ticketDescription}", view=embedButtons(timeout=None))
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        TicketData.add(connection, cursor, tchannel.id, author.id, f"{now} UTC", ticketType, "Active", message2.id)
        TicketData.close(connection)
        embed2 = discord.Embed(title='Ticket Created', description=f'{author.mention} has created a new ticket', color=embedColor)
        embed2.add_field(name='Channel:', value=f'{tchannel.mention}', inline=False)
        embed2.add_field(name=f'Reason:', value=f'{ticketDescription}', inline=False)
        embed2.add_field(name='Type:', value=f'{ticketType}', inline=False)
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=bot.user.display_avatar)
        syslogc = await bot.fetch_channel(ticketLogsChannelID)
        try:
            message3 = await syslogc.send(embed=embed2)
        except discord.HTTPException:
            message3 = await syslogc.send(f"Ticket Created by {author}, Reason: {ticketDescription}")
        del x[interaction.user.display_name]

class TicketCreation(discord.ui.View):
    @discord.ui.button(label="Create a new ticket", emoji="📩", style=discord.ButtonStyle.blurple)
    async def presscreate(self, interaction:discord.Interaction, button:discord.ui.button):
        author = interaction.user
        guild = interaction.guild
        if multipleTicketsAllowed == False:
            connection = TicketData.connect()
            cursor = TicketData.cursor(connection)
            allTickets = []
            allTickets = TicketData.getall(cursor, allTickets)
            alreadyOpened = False
            for tickets in allTickets:
                if (int(tickets[1])) == author.id and (str(tickets[5])) != ("Archived"):
                    alreadyOpened = True
                    activeChannel = int(tickets[0])
                    break
                else:
                    pass
            if alreadyOpened == True:
                achannel = get(guild.channels, id=activeChannel)
                embed2 = discord.Embed(description=f"You can't have more than one ticket open at a time! Please close your current ticket before opening a new one.", color=embedColor)
                embed2.add_field(name="**__Open Tickets:__**", value=f"{achannel.mention}")
                embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                await interaction.response.send_message(embed=embed2, ephemeral=True)
            else:
                embed2 = discord.Embed(description=f'Hi there {author.name}! Please select a ticket option from the drop-down list below!', color=embedColor)
                embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
                await interaction.response.send_message(embed=embed2, view=TicketCreationMenuUI(), ephemeral=True)
        else:
            embed2 = discord.Embed(description=f'Hi there {author.name}! Please select a ticket option from the drop-down list below!', color=embedColor)
            embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
            embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
            await interaction.response.send_message(embed=embed2, view=TicketCreationMenuUI(), ephemeral=True)
    
x = dict() 