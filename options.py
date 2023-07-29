import discord
import asyncio
import io
import chat_exporter
from discord.utils import get
from config import *
from database import *
from bot import *

class addMemberModal(discord.ui.Modal, title="Add a member"):
    answer = discord.ui.TextInput(label='Place Member ID here', style=discord.TextStyle.short, required=True, max_length=128)

    async def on_submit(self, interaction: discord.Interaction):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        TicketData.close(connection)
        try:
            ltype = (ticketInfo[4])
        except IndexError:
            ltype = str("N/A")
        
        try:
            amember = discord.utils.get(guild.members, id=int(self.children[0].value))
        except Exception:
            amember = None
        if amember == None:
            embed = discord.Embed(description=f'''I couldn't find that member, are you sure that is a valid member id? This is what I got: {self.children[0].value}''', color=embedColor)
            embed.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            embed.set_author(name=f'{author}', icon_url=author.display_avatar)
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''I couldn't find that member, are you sure that is a valid member id? This is what I got: {self.children[0].value}''', ephemeral=True)
        elif amember != None:
            allowedAccess = False
            try:
                for allowedRoles in list(channelPerms[f"{ltype}"]):
                    prole = discord.utils.get(guild.roles, id=allowedRoles)
                    if prole in amember.roles:
                        allowedAccess = True
                        break
                    else:
                        pass
            except TypeError:
                prole = get(guild.roles, id=channelPerms[f"{ltype}"])
                if prole in amember.roles:
                    allowedAccess = True
                else:
                    pass
            if (allowedAccess == True):
                embed2 = discord.Embed(description=f'''I can't add that member!''', color=embedColor)
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
                try:
                    await interaction.response.send_message(embed=embed2, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''I can't add that member!`''', ephemeral=True)
            else:
                await tchannel.set_permissions(amember, send_messages=True, read_messages=True)
                embed2 = discord.Embed(description=f'''Member added. ✅''', color=embedColor)
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
                try:
                    await interaction.response.send_message(embed=embed2, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''Member added. ✅''', ephemeral=True)
                embed3 = discord.Embed(title="**__Member Added__**", description=f'''{amember.mention} has been added to the ticket by {author.mention}''', color=embedColor)
                embed3.set_thumbnail(url=f'{amember.avatar}')
                embed3.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                try:
                    await tchannel.send(embed=embed3)
                except discord.HTTPException:
                    await tchannel.send(f'{amember.mention} **has been added to the ticket by {author.mention}**')

class removeMemberModal(discord.ui.Modal, title="Remove a member"):
    answer = discord.ui.TextInput(label='Place Member ID here', style=discord.TextStyle.short, required=True, max_length=128)

    async def on_submit(self, interaction: discord.Interaction):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        TicketData.close(connection)
        try:
            ltype = (ticketInfo[4])
        except IndexError:
            ltype = str("N/A")
        
        try:
            amember = discord.utils.get(guild.members, id=int(self.children[0].value))
        except Exception:
            amember = None
        if amember == None:
            embed = discord.Embed(description=f'''I couldn't find that member, are you sure that is a valid member id? This is what I got: {self.children[0].value}''', color=embedColor)
            embed.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            embed.set_author(name=f'{author}', icon_url=author.display_avatar)
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''I couldn't find that member, are you sure that is a valid member id? This is what I got: {self.children[0].value}''', ephemeral=True)
        elif amember != None:
            allowedAccess = False
            try:
                for allowedRoles in list(channelPerms[f"{ltype}"]):
                    prole = discord.utils.get(guild.roles, id=allowedRoles)
                    if prole in amember.roles:
                        allowedAccess = True
                        break
                    else:
                        pass
            except TypeError:
                prole = get(guild.roles, id=channelPerms[f"{ltype}"])
                if prole in amember.roles:
                    allowedAccess = True
                else:
                    pass
            if (allowedAccess == True):
                embed2 = discord.Embed(description=f'''I can't remove that member!''', color=embedColor)
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
                try:
                    await interaction.response.send_message(embed=embed2, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''I can't remove that member!`''', ephemeral=True)
            else:
                await tchannel.set_permissions(amember, send_messages=False, read_messages=False)
                embed2 = discord.Embed(description=f'''Member removed. ✅''', color=embedColor)
                embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
                embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
                try:
                    await interaction.response.send_message(embed=embed2, ephemeral=True)
                except discord.HTTPException:
                    await interaction.response.send_message(f'''Member removed. ✅''', ephemeral=True)

class renameChannelModal(discord.ui.Modal, title="Rename a Ticket Channel"):
    answer = discord.ui.TextInput(label='Place new name of ticket channel here', style=discord.TextStyle.short, required=True, max_length=32)
    async def on_submit(self, interaction: discord.Interaction):
        tchannel = interaction.channel
        author = interaction.user
        if f"{self.children[0].value}" == '':
            embed4 = discord.Embed(description=f'''You didn't provide a valid answer! Please try again. I got {self.children[0].value}''', color=embedColor)
            embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.send_message(embed=embed4, ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(f'''You didn't provide a valid answer! Please try again. I got {self.children[0].value}''', ephemeral=True)
        else:
            embed2 = discord.Embed(description=f'Channel Renamed ✅', color=embedColor)
            embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            await tchannel.edit(name=self.children[0].value)
            await interaction.response.send_message(embed=embed2, ephemeral=True)

    
class optionsMenu(discord.ui.View):
    @discord.ui.button(label="Claim this Ticket", emoji="🚩", style=discord.ButtonStyle.gray)
    async def claim(self, interaction:discord.Interaction, button: discord.Button):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        syslogc = get(guild.channels, id=ticketLogsChannelID)
        if (ticketInfo[2]) != "No":
            embed1 = discord.Embed(description=f'This ticket has already been claimed!', color=embedColor)
            embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.edit_message(embed=embed1, view=None)
            except discord.HTTPException:
                await interaction.response.edit_message(f"This ticket has already been claimed!", view=None)
        else:
            embed3 = discord.Embed(description=f'Ticket Claimed ✅', color=embedColor)
            embed3.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed3.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.edit_message(embed=embed3, view=None)
            except discord.HTTPException:
                await interaction.response.edit_message(f"Ticket Claimed ✅", view=None)
            
            embed2 = discord.Embed(title="**__Ticket Claimed__**", description=f'''{author.mention} has claimed this ticket.''', color=embedColor)
            embed2.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await tchannel.send(embed=embed2)
            except discord.HTTPException:
                await tchannel.send(f'''**__Ticket Claimed__**\n{author.mention} has claimed this ticket.''')
            TicketData.edit(connection, cursor, ticketInfo, author.id, ticketInfo[5])
            embed1 = discord.Embed(title='Ticket Claimed', description=f'{author.mention} has claimed ticket {tchannel.mention}', color=embedColor)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                message2 = await syslogc.send(embed=embed1)
            except discord.HTTPException:
                message2 = await syslogc.send(f"**{author.mention} has claimed ticket {tchannel.mention}**")
            else:
                pass
        TicketData.close(connection)

    @discord.ui.button(label="Add a member", emoji="👥", style=discord.ButtonStyle.green)
    async def addmember(self, interaction:discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(addMemberModal())
        author = interaction.user
        embed2 = discord.Embed(description=f'You can only push a button once!', color=embedColor)
        embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
        await interaction.edit_original_response(embed=embed2, view=None)

    @discord.ui.button(label="Remove a member", emoji="👋", style=discord.ButtonStyle.red)
    async def removemember(self, interaction:discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(removeMemberModal())
        author = interaction.user
        embed2 = discord.Embed(description=f'You can only push a button once!', color=embedColor)
        embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
        await interaction.edit_original_response(embed=embed2, view=None)

    @discord.ui.button(label="Active Ticket", emoji="🟢", style=discord.ButtonStyle.blurple)
    async def activeticket(self, interaction:discord.Interaction, button: discord.ui.button):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        syslogc = get(guild.channels, id=ticketLogsChannelID)
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        categoryn = activeTicketsCategoryID
        if tchannel.category_id != categoryn:
            embed4 = discord.Embed(description=f'Setting Ticket to `Active` status...', color=embedColor)
            embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                message3 = await interaction.response.edit_message(embed=embed4, view=None)
            except discord.HTTPException:
                message3 = await interaction.response.edit_message(f"Setting Ticket to `Active` status...", view=None)
            category = discord.utils.get(guild.categories, id=categoryn)
            await tchannel.edit(category=category)
            TicketData.edit(connection, cursor, ticketInfo, ticketInfo[2], "Active")
            embed1 = discord.Embed(title='__**Ticket Status Changed**__', description=f'This ticket has been set to `Active` ✅', color=embedColor)
            embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                message3 = await tchannel.send(embed=embed1)
            except discord.HTTPException:
                message3 = await tchannel.send(f"**This ticket has been set to `Active` ✅**")
            embed2 = discord.Embed(title='Ticket set to Active', description=f'Ticket {tchannel.mention} has been set to `Active` by {author.mention}', color=embedColor)
            embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await syslogc.send(embed=embed2)
            except discord.HTTPException:
                await syslogc.send(f"Ticket {tchannel.mention} has been set to `Active` by {author.mention}")   
        elif tchannel.category_id == categoryn:
            embed1 = discord.Embed(description=f'This ticket is already set to `Active`!', color=embedColor)
            embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.edit_message(embed=embed1, view=None)
            except discord.HTTPException:
                await tchannel.send(f"This ticket is already set to `Active`!")
        TicketData.close(connection)

    @discord.ui.button(label="Onhold Ticket", emoji="✋", style=discord.ButtonStyle.blurple)
    async def onholdticket(self, interaction:discord.Interaction, button: discord.ui.button):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        syslogc = get(guild.channels, id=ticketLogsChannelID)
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        categoryn = onHoldTicketsCategoryID
        if tchannel.category_id != categoryn:
            embed4 = discord.Embed(description=f'Setting Ticket to `Onhold` status...', color=embedColor)
            embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                message3 = await interaction.response.edit_message(embed=embed4, view=None)
            except discord.HTTPException:
                message3 = await interaction.response.edit_message(f"Setting Ticket to `Onhold` status...", view=None)
            category = discord.utils.get(guild.categories, id=categoryn)
            await tchannel.edit(category=category)
            TicketData.edit(connection, cursor, ticketInfo, ticketInfo[2], "Onhold")
            embed1 = discord.Embed(title='__**Ticket Status Changed**__', description=f'This ticket has been set to `Onhold` ✅', color=embedColor)
            embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                message3 = await tchannel.send(embed=embed1)
            except discord.HTTPException:
                message3 = await tchannel.send(f"**This ticket has been set to `Onhold` ✅**")
            embed2 = discord.Embed(title='Ticket set to Onhold', description=f'Ticket {tchannel.mention} has been set to `Onhold` by {author.mention}', color=embedColor)
            embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await syslogc.send(embed=embed2)
            except discord.HTTPException:
                await syslogc.send(f"Ticket {tchannel.mention} has been set to `Onhold` by {author.mention}")   
        elif tchannel.category_id == categoryn:
            embed1 = discord.Embed(description=f'This ticket is already set to `Onhold`!', color=embedColor)
            embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
            embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
            try:
                await interaction.response.edit_message(embed=embed1, view=None)
            except discord.HTTPException:
                await tchannel.send(f"This ticket is already set to `Onhold`!")
        TicketData.close(connection)

    @discord.ui.button(label="Rename Ticket", emoji="✏️", style=discord.ButtonStyle.gray)
    async def rename(self, interaction:discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(renameChannelModal())
        author = interaction.user
        embed2 = discord.Embed(description=f'You can only select a button once!', color=embedColor)
        embed2.set_author(name=f'{author}', icon_url=f'{author.display_avatar}')
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')  
        await interaction.edit_original_response(embed=embed2, view=None)
        
    @discord.ui.button(label="Archive Ticket", emoji="🗄️", style=discord.ButtonStyle.blurple)
    async def archive(self, interaction:discord.Interaction, button: discord.ui.button):
        author = interaction.user
        embed6 = discord.Embed(description="Are you sure that you want to archive this ticket? This will result in the ticket being moved to the archived category and the ticket will no longer be managed by the ticketbot.", color=embedColor)
        embed6.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed6.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.edit_message(embed=embed6, view=ticketArchiveyesOrNoOption(timeout=None))
        except discord.HTTPException:
            await interaction.response.edit_message(content="Something weird happened here, try again.")

    @discord.ui.button(label="Transcribe Ticket", emoji="📝", style=discord.ButtonStyle.red)
    async def transcribe(self, interaction:discord.Interaction, button: discord.ui.button):
        author = interaction.user
        embed6 = discord.Embed(description="Are you sure that you want to close this ticket? This will result in the ticket being deleted.", color=embedColor)
        embed6.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed6.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.edit_message(embed=embed6, view=yesOrNoOption(timeout=None))
        except discord.HTTPException:
            await interaction.response.edit_message("Something weird happened here, try again.")


class yesOrNoOption(discord.ui.View):
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction:discord.Interaction, button: discord.ui.button):
        tchannel = interaction.channel
        lchannel = bot.get_channel(ticketTranscriptChannelID)
        author = interaction.user
        guild = interaction.guild
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        syslogc = get(guild.channels, id=ticketLogsChannelID)
        embed4 = discord.Embed(description=f'Transcribing Ticket...', color=embedColor)
        embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.edit_message(embed=embed4, view=None)
        except discord.HTTPException:
            await interaction.response.edit_message(f"Transcribing Ticket...", )
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        embed3 = discord.Embed(title=f'Ticket Closed', description=f'{author.mention} has closed this ticket, it will be logged and deleted within 5 seconds.', color=embedColor)
        embed3.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await tchannel.send(embed=embed3)
        except discord.HTTPException:
            await tchannel.send(f"{author.mention} has closed this ticket, it will be logged and deleted within 5 seconds.")
        await asyncio.sleep(2)
        transcript = await chat_exporter.export(tchannel)
        transcript_file = discord.File(io.BytesIO(transcript.encode()),
                                       filename=f"transcript-{tchannel.name}_{tchannel.id}.html") 
        transcript_message = await lchannel.send(file=transcript_file)
        tauthor = await bot.fetch_user(int(ticketInfo[1]))
        embed2 = discord.Embed(title=f'Ticket Transcribed', description=f'A open ticket has been marked as closed by {author.mention}, it has been logged and deleted.', color=embedColor)
        embed2.set_thumbnail(url="https://static-00.iconduck.com/assets.00/memo-emoji-1948x2048-bgnk0vsq.png")
        embed2.set_author(name=author, icon_url=author.display_avatar)
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        embed2.add_field(name='**__Channel Name:__**', value=f'#{tchannel.name}', inline=True)
        embed2.add_field(name="**__Author:__**", value=f"{tauthor.mention}", inline=True)
        embed2.add_field(name="**__Type:__**", value=f"{ticketInfo[4]}", inline=True)
        if dmTicketCopies == True:
            try:
                transcript_file1 = discord.File(io.BytesIO(transcript.encode()),
                                       filename=f"transcript-{tchannel.name}_{tchannel.id}.html") 
                transcript_message1 = await tauthor.send(file=transcript_file1)
                embed3 = discord.Embed(title="Ticket Copy", description=f"Hi {tauthor.mention}!\n Thank you for creating a ticket with us. Attached to this message is a copy of your ticket for your records.\n\nPlease note, any media sent in your ticket will not load in the copy after a couple of days.\n \n ", color=embedColor)
                embed3.add_field(name="**__Jump/Download Link:__**", value=f"{transcript_message1.jump_url}", inline=True)
                transcript_url1 = ("https://webthedev.me/ticketviewer/?url="+ transcript_message1.attachments[0].url)
                embed3.add_field(name="**__View Link:__**", value=f"[Click here!]({transcript_url1})", inline=True)
                embed3.set_thumbnail(url="https://static-00.iconduck.com/assets.00/memo-emoji-1948x2048-bgnk0vsq.png")
                try:
                    await tauthor.send(embed=embed3)
                except discord.HTTPException:
                    await tauthor.send(f"Hi {tauthor.mention}!\n Thank you for creating a ticket with us. Attached to this message is a copy of your ticket for your records.\nPlease note, any media sent in your ticket will not load in the copy after a couple of days.\n**__Jump/Download Link:__{transcript_message.jump_url}\n**__View Link:__**[Click here!]({transcript_url1})")
                embed2.add_field(name="**__Copy Status:__**", value="A copy of the ticket was successfully delivered to the ticket creator. ✅")
            except Exception:
                embed2.add_field(name="**__Copy Status:__**", value="The copy failed to be delivered to the ticket creator. This is most likely due to their dms being off. ❌")
        else:
            pass
        embed2.add_field(name="**__Time Created:__**", value=f"{ticketInfo[3]}", inline=False)
        embed2.add_field(name="**__Jump/Download Link:__**", value=f"\n{transcript_message.jump_url}", inline=True)
        transcript_url = ("https://webthedev.me/ticketviewer/?url="+ transcript_message.attachments[0].url)
        embed2.add_field(name="**__View Link:__**", value=f"\n[Click here!]({transcript_url})", inline=True)
        try:
            message3 = await syslogc.send(embed=embed2)
        except discord.HTTPException:
            message3 = await syslogc.send(f"Ticket Channel **{tchannel.mention}** was closed by {author.mention}, it has been logged and deleted.")
        await tchannel.delete()
        TicketData.delete(connection, cursor, tchannel.id)
        TicketData.close(connection)
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction:discord.Interaction, button: discord.ui.button):
        author = interaction.user
        embed4 = discord.Embed(description="Aborting...", color=embedColor)
        embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.edit_message(embed=embed4, view=None)
        except discord.HTTPException:
            await interaction.response.edit_message("Aborting...", view=None)

class ticketArchiveyesOrNoOption(discord.ui.View):
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction:discord.Interaction, button: discord.ui.button):
        tchannel = interaction.channel
        author = interaction.user
        guild = interaction.guild
        syslogc = get(guild.channels, id=ticketLogsChannelID)
        connection = TicketData.connect()
        cursor = TicketData.cursor(connection)
        ticketInfo = TicketData.find(cursor, tchannel.id)
        categoryn = archivedTicketsCategoryID
        embed4 = discord.Embed(description=f'Setting Ticket to `Archived` status...', color=embedColor)
        embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            message3 = await interaction.response.edit_message(embed=embed4, view=None)
        except discord.HTTPException:
            message3 = await interaction.response.edit_message(f"Setting Ticket to `Archived` status...", view=None)
        category = discord.utils.get(guild.categories, id=categoryn)
        await tchannel.edit(category=category)
        TicketData.edit(connection, cursor, ticketInfo, ticketInfo[2], "Archived")
        embed1 = discord.Embed(title='__**Ticket Status Changed**__', description=f'This ticket has been set to `Archived` ✅', color=embedColor)
        embed1.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed1.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            message3 = await tchannel.send(embed=embed1)
        except discord.HTTPException:
            message3 = await tchannel.send(f"**This ticket has been set to `Archived` ✅**")
        embed2 = discord.Embed(title='Ticket set to Archived', description=f'Ticket {tchannel.mention} has been set to `Archived` by {author.mention}', color=embedColor)
        embed2.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await syslogc.send(embed=embed2)
        except discord.HTTPException:
            await syslogc.send(f"Ticket {tchannel.mention} has been set to `Archived` by {author.mention}")   
        TicketData.delete(connection, cursor, tchannel.id)
        TicketData.close(connection)
    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction:discord.Interaction, button: discord.ui.button):
        author = interaction.user
        embed4 = discord.Embed(description="Aborting...", color=embedColor)
        embed4.set_author(name=f'{author}', icon_url=author.display_avatar)
        embed4.set_footer(text=f"{footerOfEmbeds} | {bot.user.id}", icon_url=f'{bot.user.display_avatar}')
        try:
            await interaction.response.edit_message(embed=embed4, view=None)
        except discord.HTTPException:
            await interaction.response.edit_message("Aborting...", view=None)