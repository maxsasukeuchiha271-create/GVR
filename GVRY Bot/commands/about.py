import discord
from discord import app_commands
from discord.ext import commands
import time

class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="about", description="View information about Greenville Roleplay Yowe and the bot")
    async def about(self, interaction: discord.Interaction):
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        
        embed = self.bot.format_embed(self.bot.config, 'about',
            developer="<@915035696778067999>",
            uptime=uptime_str,
            guilds=len(self.bot.guilds),
            library=f"discord.py {discord.__version__}"
        )
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(About(bot))
