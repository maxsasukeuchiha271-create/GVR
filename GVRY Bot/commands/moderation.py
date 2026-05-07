import discord
import uuid
from discord import app_commands
from discord.ext import commands
from database import Database

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="User to ban", reason="Reason for ban", proof="Proof link/image")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str, proof: str):
        hc_id = int(self.bot.config['roles']['high_command'])
        overseer_id = int(self.bot.config['roles']['overseer'])

        if not any(r.id in [hc_id, overseer_id] for r in interaction.user.roles):
            return await interaction.response.send_message("Only High Command can use this command.", ephemeral=True)
        
        ban_id = f"BAN-{uuid.uuid4().hex[:6].upper()}"
        await interaction.guild.ban(user, reason=reason)
        await Database.execute("INSERT INTO moderation (id, user_id, type, reason, proof, moderator_id) VALUES (?, ?, 'ban', ?, ?, ?)", 
                               (ban_id, str(user.id), reason, proof, str(interaction.user.id)))
        await interaction.response.send_message(f"Banned {user.name} (ID: {ban_id}).")

    @app_commands.command(name="strike", description="Issue a strike to a user")
    @app_commands.describe(user="User to strike", reason="Reason for strike", proof="Proof link/image", count="Number of strikes")
    async def strike(self, interaction: discord.Interaction, user: discord.Member, reason: str, proof: str, count: int = 1):
        hc_id = int(self.bot.config['roles']['high_command'])
        overseer_id = int(self.bot.config['roles']['overseer'])

        if not any(r.id in [hc_id, overseer_id] for r in interaction.user.roles):
            return await interaction.response.send_message("Only High Command can use this command.", ephemeral=True)
        
        for _ in range(count):
            strike_id = f"STR-{uuid.uuid4().hex[:6].upper()}"
            await Database.execute("INSERT INTO moderation (id, user_id, type, reason, proof, moderator_id) VALUES (?, ?, 'strike', ?, ?, ?)", 
                                   (strike_id, str(user.id), reason, proof, str(interaction.user.id)))
        await interaction.response.send_message(f"Struck {user.name} x{count}.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))