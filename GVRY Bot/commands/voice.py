import discord
from discord import app_commands
from discord.ext import commands

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="joinvc", description="Make the bot join a voice channel")
    @app_commands.describe(voicechat="The voice channel to join")
    async def joinvc(self, interaction: discord.Interaction, voicechat: discord.VoiceChannel):
        # Staff role check
        STAFF_ROLE_ID = 1474665732133486592
        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("Only staff team members can use this command.", ephemeral=True)

        # Check permissions
        permissions = voicechat.permissions_for(interaction.guild.me)
        if not permissions.connect or not permissions.speak:
            return await interaction.response.send_message(f" I do not have permission to join or speak in {voicechat.mention}.", ephemeral=True)

        try:
            # Check if the bot is already in a voice channel in this guild
            if interaction.guild.voice_client:
                # Move to the new channel if already connected
                await interaction.guild.voice_client.move_to(voicechat)
            else:
                # Connect to the channel - setting self_deaf to True helps with stability
                await voicechat.connect(self_deaf=True)
            
            embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Voice Channel Joined___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038> Successfully connected to **{voicechat.mention}**.",
                color=0xadcf8b,
                timestamp=discord.utils.utcnow()
            )
            
            embed.set_footer(
                text=interaction.client.config['bot']['footer_text'],
                icon_url=interaction.client.config['bot']['footer_icon']
            )
            
            await interaction.response.send_message(embed=embed)
            
        except discord.ClientException as e:
            if "PyNaCl" in str(e):
                await interaction.response.send_message(" **Voice support error:** The `PyNaCl` library is missing or improperly installed. Please run `pip install PyNaCl` on the bot's host.", ephemeral=True)
            else:
                await interaction.response.send_message(f" A voice client error occurred: {e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f" An unexpected error occurred: {e}", ephemeral=True)

    @app_commands.command(name="leavevc", description="Make the bot leave the voice channel")
    async def leavevc(self, interaction: discord.Interaction):
        # Staff role check
        STAFF_ROLE_ID = 1474665732133486592
        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("Only staff team members can use this command.", ephemeral=True)

        if not interaction.guild.voice_client:
            return await interaction.response.send_message(" I am not connected to any voice channel.", ephemeral=True)

        await interaction.guild.voice_client.disconnect()
        
        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Voice Channel Left___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description="> <a:recolored_arrowmove:1499985868541133038> Successfully disconnected from the voice channel.",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Voice(bot))