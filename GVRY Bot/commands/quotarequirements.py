import discord
from discord import app_commands
from discord.ext import commands

class QuotaRequirements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quotarequirements", description="Sends embed with staff quota requirements")
    async def quotarequirements(self, interaction: discord.Interaction):
        allowed_roles = interaction.client.config.get('permissions', {}).get('quotarequirements', [])
        if not any(role.id in [int(r) for r in allowed_roles] for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        embed = self.bot.format_embed(self.bot.config, 'quota_requirements')
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message("Quota requirements sent.", ephemeral=True)
        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(QuotaRequirements(bot))
