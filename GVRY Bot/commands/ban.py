import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import uuid
from datetime import datetime
from database import Database
from main import command_permission_check

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @command_permission_check("ban")
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="The user to ban", reason="Reason for the ban", proof="Link to proof")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str, proof: str):
        uid = str(user.id)
        ban_id = f"BAN-{uuid.uuid4().hex[:6].upper()}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log to Database
        await Database.execute(
            "INSERT INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ban_id, uid, 'ban', reason, proof, str(interaction.user.id), timestamp)
        )

        try:
            embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Banned___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038>  **__Reason:__** {reason}\n> <a:recolored_arrowmove:1499985868541133038>  **__Proof:__** [Click Here]({proof})",
                color=0xadcf8b,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])
            await user.send(f" You have been banned from **{interaction.guild.name}**.", embed=embed)
        except: pass

        await interaction.guild.ban(user, reason=f"Moderator: {interaction.user} | Reason: {reason}")

        log_channel_id = interaction.client.config['channels'].get('mod_logs_channel_id')
        if log_channel_id:
            channel = interaction.guild.get_channel(int(log_channel_id))
            if channel:
                log_embed = discord.Embed( 
                    title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Ban Log___ <a:recolored_recolored_red_stars:1499985951894802553>",
                    description=f"> <a:recolored_arrowmove:1499985868541133038>  **__User:__** {user} ({user.id})\n> <a:recolored_arrowmove:1499985868541133038>  **__Moderator:__** {interaction.user.mention}\n> <a:recolored_arrowmove:1499985868541133038>  **__Reason:__** {reason}\n> <a:recolored_arrowmove:1499985868541133038>  **__Proof:__** [Click Here]({proof})",
                    color=0xadcf8b,
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])
                await channel.send(embed=log_embed)

        final_embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Success___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  Successfully banned **{user}** from the server.",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        final_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

        await interaction.response.send_message(embed=final_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ban(bot))