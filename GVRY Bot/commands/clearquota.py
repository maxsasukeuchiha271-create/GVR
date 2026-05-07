import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from database import Database

class ClearQuota(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clearquota", description="Clear hosted and co-hosted sessions for all staff profiles")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearquota(self, interaction: discord.Interaction):
        # Clear all session logs from the database
        await Database.execute("DELETE FROM staff_sessions")
        
        embed = discord.Embed(
            title="Quota Cleared",
            description="All hosted and co-hosted session logs have been cleared for all staff members.",
            color=0xadcf8b
        )
        await interaction.response.send_message(embed=embed)

    @clearquota.error
    async def clearquota_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(" You must have Administrator permissions to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f" An error occurred: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ClearQuota(bot))