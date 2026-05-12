import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from database import Database

class Modlogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="modlogs", description="Show a user's moderation logs")
    @app_commands.describe(user="The user to view logs for")
    async def modlogs(self, interaction: discord.Interaction, user: discord.User):
        if 1474665732133486592 not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Only staff team members can use this command.", ephemeral=True)

        uid = str(user.id)
        logs = await Database.fetch_all("SELECT * FROM moderation WHERE user_id = ? ORDER BY timestamp DESC", (uid,))

        if not logs:
            return await interaction.response.send_message(f"No moderation logs for {user.display_name}.", ephemeral=True)

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Legacy_ - ___Moderation Logs___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  **__User:__** {user.mention}",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        # Group logs by type
        infractions = [l for l in logs if l['type'] == 'infraction']
        strikes = [l for l in logs if l['type'] == 'strike']
        bans = [l for l in logs if l['type'] == 'ban']
        
        if infractions:
            infs = ""
            for inf in infractions[:5]:
                status = " Active" if not inf['cleared'] else " Cleared"
                infs += f"**ID:** {inf['id']} ({status})\n**Moderator:** <@{inf['moderator_id']}>\n**Reason:** {inf['reason']}\n**Proof:** [Link]({inf['proof']})\n\n"
            embed.add_field(name="Infractions (Latest 5)", value=infs or "None", inline=False)

        if strikes:
            strks = ""
            for strk in strikes[:5]:
                status = " Active" if not strk['cleared'] else " Cleared"
                strks += f"**ID:** {strk['id']} ({status})\n**Moderator:** <@{strk['moderator_id']}>\n**Reason:** {strk['reason']}\n**Proof:** [Link]({strk['proof']})\n\n"
            embed.add_field(name="Staff Strikes (Latest 5)", value=strks or "None", inline=False)

        if bans:
            bans = ""
            for ban in bans:
                bans_str += f"**Reason:** {ban['reason']}\n**Proof:** [Link]({ban['proof']})\n\n"
            embed.add_field(name="Bans", value=bans or "None", inline=False)

        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Modlogs(bot))
