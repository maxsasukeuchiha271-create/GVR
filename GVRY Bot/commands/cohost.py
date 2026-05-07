import discord
from discord import app_commands
from discord.ext import commands
from utils import format_embed

async def startup_required(interaction: discord.Interaction) -> bool:
    states = getattr(interaction.client, 'session_states', None) or {}
    if not states.get(interaction.channel_id, {}).get('completed'):
        await interaction.response.send_message(
            " You must use the `/startup` command in this channel before using other commands.", ephemeral=True
        )
        return False
    return True

async def correct_channel(interaction: discord.Interaction) -> bool:
    channels = interaction.client.config['channels']
    id1 = channels.get('session_commands_channel_id')
    id2 = channels.get('session_commands_channel_id_2')
    if str(interaction.channel_id) not in [str(id1), str(id2)]:
        await interaction.response.send_message(
            f" This command can only be used in <#{id1}> or <#{id2}>.", ephemeral=True
        )
        return False
    return True

class Cohost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cohost", description="Announce yourself as the co-host for the session")
    async def cohost(self, interaction: discord.Interaction):
        if int(interaction.client.config['roles']['staff_team']) not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return
        if not await correct_channel(interaction):
            return
        if not await startup_required(interaction):
            return

        ecfg = interaction.client.config.get('embeds', {}).get('cohost', {})
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Session Co-Host___'),
            description=format_embed(ecfg.get('description', ''), interaction.client, user=interaction.user.mention),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message("You have been announced as the co-host.", ephemeral=True)
        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cohost(bot))
