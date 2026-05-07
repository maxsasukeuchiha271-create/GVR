import discord
from discord import app_commands
from discord.ext import commands

class CoreCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="membercount", description="Show the server member count")
    async def membercount(self, interaction: discord.Interaction):
        await interaction.response.send_message("Retrieving member count...", ephemeral=True)
        embed = self.bot.format_embed(
            self.bot.config, 
            'member_count', 
            count=interaction.guild.member_count
        )
        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CoreCommands(bot))