import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# Logic moved to main.py to handle auto-verification and welcome in one event.

async def setup(bot):
    await bot.add_cog(Welcome(bot))