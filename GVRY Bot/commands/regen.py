import discord
from discord import app_commands
from discord.ext import commands

# Check if startup was completed
async def startup_required(interaction: discord.Interaction) -> bool:
    states = getattr(interaction.client, 'session_states', None) or {}
    if not states.get(interaction.channel_id, {}).get('completed'):
        await interaction.response.send_message(
            " You must use the `/startup` command in this channel before using other commands.",
            ephemeral=True
        )
        return False
    return True

# Check if the command is used in the correct channel
async def correct_channel(interaction: discord.Interaction) -> bool:
    channels = interaction.client.config['channels']
    id1 = channels.get('session_commands_channel_id')
    id2 = channels.get('session_commands_channel_id_2')
    allowed = [str(id1), str(id2)]
    if str(interaction.channel_id) not in allowed:
        await interaction.response.send_message(
            f" This command can only be used in <#{id1}> or <#{id2}>.",
            ephemeral=True
        )
        return False
    return True

class Regen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="regen", description="Announce a link regeneration")
    async def regen(self, interaction: discord.Interaction):
        allowed_roles = interaction.client.config.get('permissions', {}).get('regen', [])
        if not any(role.id in [int(r) for r in allowed_roles] for role in interaction.user.roles):
            await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return
        
        # Check if used in the correct channel
        if not await correct_channel(interaction):
            return
            
        # Check if startup was completed
        if not await startup_required(interaction):
            return

        user = interaction.user

        embed = self.bot.format_embed(self.bot.config, 'regen', user=user.mention)
        await interaction.response.send_message("Link Regenerated.", ephemeral=True)
        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Regen(bot))
