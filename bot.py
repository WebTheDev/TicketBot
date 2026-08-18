import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.all()
bot = discord.Client(command_prefix=commands.when_mentioned_or('-'), intents=intents)
ticket = app_commands.CommandTree(bot)
