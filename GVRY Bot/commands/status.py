import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Change the bot's presence status")
    @app_commands.describe(
        type="The type of activity (Playing, Watching, Listening, etc.)",
        text="The status message text",
        status="The online status (Online, Idle, DND, Invisible)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def status(
        self, 
        interaction: discord.Interaction, 
        type: Literal["Playing", "Watching", "Listening", "Competing"], 
        text: str,
        status: Literal["online", "idle", "dnd", "invisible"] = "online"
    ):
        activity_type = {
            "Playing": discord.ActivityType.playing,
            "Watching": discord.ActivityType.watching,
            "Listening": discord.ActivityType.listening,
            "Competing": discord.ActivityType.competing
        }[type]

        discord_status = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }[status]

        activity = discord.Activity(type=activity_type, name=text)
        await self.bot.change_presence(activity=activity, status=discord_status)

        embed = discord.Embed(
            title="Status Updated",
            description=f"> **Type:** {type}\n> **Text:** {text}\n> **Status:** {status.capitalize()}",
            color=0xadcf8b
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @status.error
    async def status_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(" You must have Administrator permissions to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f" An error occurred: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Status(bot))
