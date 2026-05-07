import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Make the bot say a message")
    @app_commands.describe(message="The message you want the bot to say")
    @app_commands.checks.has_permissions(administrator=True)
    async def say(self, interaction: discord.Interaction, message: str):
        # Send the message to the channel
        await interaction.channel.send(message)
        # Send a private confirmation to the user
        await interaction.response.send_message("Message sent.", ephemeral=True)

    @say.error
    async def say_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(" Only people with administrator permissions can use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f" An error occurred: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Say(bot))
