import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import uuid
from datetime import datetime
from database import Database
from main import command_permission_check

class Strike(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @command_permission_check("strike")
    @app_commands.command(name="strike", description="Issue a staff strike to a user")
    @app_commands.describe(user="The user to strike", reason="Reason for the strike", proof="Link to proof", count="How many strikes to give")
    async def strike(self, interaction: discord.Interaction, user: discord.Member, reason: str, proof: str, count: int = 1):
        await interaction.response.defer(ephemeral=True)

        try:
            uid = str(user.id)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            new_strikes = []
            for _ in range(count):
                strk_id = f"STR-{uuid.uuid4().hex[:6].upper()}"
                await Database.execute(
                    "INSERT INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (strk_id, uid, 'strike', reason, proof, str(interaction.user.id), timestamp)
                )
                new_strikes.append(strk_id)

            active_res = await Database.fetch_all("SELECT id FROM moderation WHERE user_id = ? AND type = 'strike' AND cleared = 0", (uid,))
            total_strk = len(active_res)

            roles_config = interaction.client.config['roles']
            STRK_ROLES = [
                int(roles_config['strike_1']),
                int(roles_config['strike_2']),
                int(roles_config['strike_3'])
            ]
            STAFF_SUSPENSION_ID = int(roles_config['staff_suspension'])
            STAFF_ROLE_ID = 1474665732133486592
            COUNCIL_ROLE_ID = 1452886793278984315

            if total_strk >= 3:
                # Add staff suspension role
                susp_role = interaction.guild.get_role(STAFF_SUSPENSION_ID)
                if susp_role and susp_role not in user.roles:
                    await user.add_roles(susp_role)
                
                # Remove staff and council roles
                for r_id in [STAFF_ROLE_ID, COUNCIL_ROLE_ID]:
                    r = interaction.guild.get_role(r_id)
                    if r and r in user.roles:
                        await user.remove_roles(r)
                
                # Remove individual strike roles
                for r_id in STRK_ROLES:
                    r = interaction.guild.get_role(r_id)
                    if r and r in user.roles:
                        await user.remove_roles(r)
            else:
                # Apply strike level roles for 1 or 2 strikes
                for i in range(min(total_strk, len(STRK_ROLES))):
                    role = interaction.guild.get_role(STRK_ROLES[i])
                    if role and role not in user.roles:
                        await user.add_roles(role)

            ids_str = ', '.join(new_strikes)
            try:
                embed = self.bot.format_embed(self.bot.config, 'strike_issued',
                    user=user.mention, moderator=interaction.user.mention, reason=reason, proof=proof, count=count, ids=ids_str
                )
                embed.timestamp = discord.utils.utcnow()
                await user.send(f"You have received {count} staff strike(s).", embed=embed)
            except: pass

            log_channel_id = interaction.client.config['channels'].get('mod_logs_channel_id')
            if log_channel_id:
                channel = interaction.guild.get_channel(int(log_channel_id))
                if channel:
                    log_embed = self.bot.format_embed(self.bot.config, 'strike_issued',
                        user=user.mention, moderator=interaction.user.mention, reason=reason, proof=proof, count=count, ids=ids_str
                    )
                    log_embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=log_embed)

            followup_embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Success___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038>  Successfully issued **{count}** staff strike(s) to {user.mention}.",
                color=0xadcf8b
            )
            followup_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

            await interaction.followup.send(embed=followup_embed)
        except Exception as e:
            await interaction.followup.send(f" An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Strike(bot))