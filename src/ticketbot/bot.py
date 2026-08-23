import discord
from discord import app_commands

intents = discord.Intents.all()
bot = discord.Client(intents=intents)
ticket = app_commands.CommandTree(bot)
