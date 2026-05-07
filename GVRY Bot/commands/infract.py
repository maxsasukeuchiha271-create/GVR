import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import uuid
from datetime import datetime
from database import Database
from main import command_permission_check

class Infract(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @command_permission_check("infract")
    @app_commands.command(name="infract", description="Issue an infraction to a user")
    @app_commands.describe(user="The user to infract", reason="Reason for the infraction", proof="Link to proof", count="How many infractions to give")
    async def infract(self, interaction: discord.Interaction, user: discord.Member, reason: str, proof: str, count: int = 1):
        await interaction.response.defer(ephemeral=True)

        try:
            uid = str(user.id)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            new_infractions = []
            for _ in range(count):
                inf_id = f"INF-{uuid.uuid4().hex[:6].upper()}"
                await Database.execute(
                    "INSERT INTO moderation (id, user_id, type, reason, proof, moderator_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (inf_id, uid, 'infraction', reason, proof, str(interaction.user.id), timestamp)
                )
                new_infractions.append(inf_id)

            # Fetch current active infractions count
            active_res = await Database.fetch_all("SELECT id FROM moderation WHERE user_id = ? AND type = 'infraction' AND cleared = 0", (uid,))
            total_inf = len(active_res)
            
            roles_config = interaction.client.config['roles']
            INF_ROLES = [
                int(roles_config['infraction_1']),
                int(roles_config['infraction_2']),
                int(roles_config['infraction_3'])
            ]
            CIV_SUSPENSION_ID = int(roles_config['civilian_suspension'])
            
            if total_inf >= 3:
                # Clear all infractions as they reached the limit
                await Database.execute(
                    "UPDATE moderation SET cleared = 1, cleared_by = ?, cleared_reason = ? WHERE user_id = ? AND type = 'infraction' AND cleared = 0",
                    (str(interaction.client.user.id), "Reached 3 active infractions limit.", uid)
                )

                # Remove existing infraction roles
                for r_id in INF_ROLES:
                    r = interaction.guild.get_role(r_id)
                    if r and r in user.roles:
                        await user.remove_roles(r)
                
                # Add the specific role for reaching suspension
                susp_role = interaction.guild.get_role(CIV_SUSPENSION_ID)
                if susp_role and susp_role not in user.roles:
                    await user.add_roles(susp_role)
            else:
                for i in range(min(total_inf, len(INF_ROLES))):
                    role = interaction.guild.get_role(INF_ROLES[i])
                    if role and role not in user.roles:
                        await user.add_roles(role)

            ids_str = ', '.join(new_infractions)
            try:
                embed = self.bot.format_embed(self.bot.config, 'infraction_issued',
                    user=user.mention, moderator=interaction.user.mention, reason=reason, proof=proof, count=count, ids=ids_str
                )
                embed.timestamp = discord.utils.utcnow()
                await user.send(f"You have received {count} infraction(s).", embed=embed)
            except: pass

            log_channel_id = interaction.client.config['channels'].get('mod_logs_channel_id')
            if log_channel_id:
                channel = interaction.guild.get_channel(int(log_channel_id))
                if channel:
                    log_embed = self.bot.format_embed(self.bot.config, 'infraction_issued',
                        user=user.mention, moderator=interaction.user.mention, reason=reason, proof=proof, count=count, ids=ids_str
                    )
                    log_embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=log_embed)

            followup_embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Success___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038>  Successfully issued **{count}** infraction(s) to {user.mention}.",
                color=0xadcf8b
            )
            followup_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

            await interaction.followup.send(embed=followup_embed)
        except Exception as e:
            await interaction.followup.send(f" An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Infract(bot))