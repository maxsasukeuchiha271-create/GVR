import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
import json
from datetime import datetime
from database import Database

class SessionLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sessionlog", description="Log a completed session to your staff profile")
    @app_commands.describe(
        session_type="Were you the Host or Co-Host?",
        start_time="Session start time",
        end_time="Session end time",
        notes="Session notes"
    )
    async def sessionlog(
        self, 
        interaction: discord.Interaction, 
        session_type: Literal["Host", "Co-Host"],
        start_time: str,
        end_time: str,
        notes: str
    ):
        # Check if user has staff role
        if 1474665732133486592 not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return

        await Database.execute(
            "INSERT INTO staff_sessions (user_id, session_type, session_date, start_time, end_time, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (str(interaction.user.id), session_type, datetime.now().strftime("%Y-%m-%d"), start_time, end_time, notes)
        )

        await interaction.response.send_message(f"Your session as **{session_type}** has been logged to your profile.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SessionLog(bot))