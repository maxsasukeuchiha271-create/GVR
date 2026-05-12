import discord
from discord import app_commands
from discord.ext import commands

class DM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dm", description="Send a direct message to a user via the bot")
    @app_commands.describe(user="The user to message", message="The content of the message")
    @app_commands.checks.has_permissions(administrator=True)
    async def dm(self, interaction: discord.Interaction, user: discord.User, message: str):
        try:
            embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Legacy_ - ___New Message___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038>  {message}",
                color=0xadcf8b,
                # timestamp=discord.utils.utcnow()
            )
            embed.set_footer(
                text=interaction.client.config['bot']['footer_text'],
                icon_url=interaction.client.config['bot']['footer_icon']
            )
            
            await user.send(embed=embed)
            await interaction.response.send_message(f"Successfully sent DM to {user.mention}.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message(f"Could not DM {user.mention}. Their DMs might be closed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @dm.error
    async def dm_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(" Only people with administrator permissions can use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DM(bot))
