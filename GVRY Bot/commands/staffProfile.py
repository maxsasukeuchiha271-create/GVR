import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from database import Database

class ProfileView(discord.ui.View):
    def __init__(self, user_id: str, user_name: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name

    async def show_history(self, interaction: discord.Interaction, log_type: str):
        # log_type is "hosted" or "cohosted" from the button, map to DB type
        await interaction.response.defer(ephemeral=False)
        db_type = "Host" if log_type == "hosted" else "Co-Host"
        sessions = await Database.fetch_all(
            "SELECT * FROM staff_sessions WHERE user_id = ? AND session_type = ? ORDER BY id DESC LIMIT 10",
            (self.user_id, db_type)
        )
        
        if not sessions:
            return await interaction.followup.send(f"No {log_type} sessions found.", ephemeral=False)

        embed = discord.Embed(
            title=f"{log_type.capitalize()} History - {self.user_name}",
            color=0xadcf8b
        )
        
        for i, s in enumerate(sessions):
            date_str = s['session_date'] or "Unknown Date"
            embed.add_field(
                name=f"Session {i+1} | {date_str}",
                value=f"**Start:** {s['start_time']} | **End:** {s['end_time']}\n**Notes:** {s['notes']}",
                inline=False
            )
            
        await interaction.followup.send(embed=embed, ephemeral=False)

    @discord.ui.button(label="Hosted Sessions", style=discord.ButtonStyle.secondary)
    async def hosted(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_history(interaction, "hosted")

    @discord.ui.button(label="Co-hosted Sessions", style=discord.ButtonStyle.secondary)
    async def cohosted(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_history(interaction, "cohosted")

class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    staff_group = app_commands.Group(name="staff", description="Staff profile commands")

    @app_commands.command(name="staffprofile", description="Direct access to your staff profile")
    @app_commands.guild_only()
    async def staffprofile_alias(self, interaction: discord.Interaction, user: discord.Member = None):
        """Alias for /staff profile"""
        # Call the actual profile logic
        await self._send_staff_profile(interaction, user or interaction.user)

    @staff_group.command(name="profile", description="View a staff member's profile")
    @app_commands.guild_only()
    @app_commands.describe(user="The staff member to view (defaults to you)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._send_staff_profile(interaction, user or interaction.user)

    async def _send_staff_profile(self, interaction: discord.Interaction, user: discord.Member):
        staff_role_id = int(interaction.client.config['roles']['staff_team'])
        
        if staff_role_id not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=False)

        await interaction.response.defer(ephemeral=False)
        uid = str(user.id)

        try:
            # Fetch Stats from DB
            strike_res = await Database.fetch_one("SELECT COUNT(*) as count FROM moderation WHERE user_id = ? AND type = 'strike' AND cleared = 0", (uid,))
            hosted_res = await Database.fetch_one("SELECT COUNT(*) as count FROM staff_sessions WHERE user_id = ? AND session_type = 'Host'", (uid,))
            cohosted_res = await Database.fetch_one("SELECT COUNT(*) as count FROM staff_sessions WHERE user_id = ? AND session_type = 'Co-Host'", (uid,))
            econ_res = await Database.fetch_one("SELECT roblox_id, roblox_username FROM economy WHERE user_id = ?", (uid,))

            roblox_id = econ_res.get('roblox_id') if econ_res else None
            roblox_user = econ_res.get('roblox_username') if econ_res else "Not Linked"

            # Auto-fetch Roblox info if missing
            if not roblox_id:
                info = await self.bot.fetch_roblox_info(user.id)
                if info:
                    roblox_id = info['roblox_id']
                    roblox_user = info['username']
                    await Database.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
                    await Database.execute(
                        "UPDATE economy SET roblox_id = ?, roblox_username = ? WHERE user_id = ?",
                        (roblox_id, roblox_user, uid)
                    )

            user_stats = {
                "strikes": strike_res['count'] if strike_res else 0,
                "hosted_count": hosted_res['count'] if hosted_res else 0,
                "cohosted_count": cohosted_res['count'] if cohosted_res else 0,
                "roblox_user": roblox_user,
                "roblox_id": roblox_id or "N/A"
            }

            # Check if the target user also has the staff role
            if staff_role_id not in [r.id for r in user.roles]:
                return await interaction.followup.send(" You can only view profiles of active staff team members.", ephemeral=False)

            roblox_display = f"[{roblox_user}](https://www.roblox.com/users/{roblox_id}/profile)" if roblox_id else "`Not Linked`"

            embed = self.bot.format_embed(self.bot.config, 'staff_profile', 
                user=user.mention, 
                strikes=user_stats['strikes'], 
                hosted=user_stats['hosted_count'], 
                cohosted=user_stats['cohosted_count'],
                roblox_user=roblox_display,
                roblox_id=user_stats['roblox_id']
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            view = ProfileView(str(user.id), user.display_name)
            await interaction.followup.send(embed=embed, view=view, ephemeral=False)
        except Exception as e:
            await interaction.followup.send(f" Failed to load staff profile: {str(e)}", ephemeral=False)

    @staff_group.command(name="leaderboard", description="Show the staff session leaderboard")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        staff_role_id = int(interaction.client.config['roles']['staff_team'])
        if staff_role_id not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=True)

        await interaction.response.defer()

        # Get all users with session data, sorted by total
        results = await Database.fetch_all("""
            SELECT user_id, 
                   COUNT(CASE WHEN session_type = 'Host' THEN 1 END) as hosted,
                   COUNT(CASE WHEN session_type = 'Co-Host' THEN 1 END) as cohosted,
                   COUNT(*) as total
            FROM staff_sessions
            GROUP BY user_id
            ORDER BY total DESC
        """)

        leaderboard_data = []
        # Only process until we find the top 10 active staff members to prevent performance lag
        for row in results:
            if len(leaderboard_data) >= 10:
                break
                
            uid = int(row['user_id'])
            member = interaction.guild.get_member(uid)
            if not member:
                try:
                    member = await interaction.guild.fetch_member(uid)
                except:
                    continue
            
            if member and staff_role_id in [r.id for r in member.roles]:
                leaderboard_data.append({
                    "member": member,
                    "hosted": row['hosted'],
                    "cohosted": row['cohosted'],
                    "total": row['total']
                })

        if not leaderboard_data:
            await interaction.followup.send("No staff members have logged sessions yet.", ephemeral=True)
            return

        description = ""
        for i, entry in enumerate(leaderboard_data[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            description += (
                f"{medal} {entry['member'].mention}\n"
                f"└ Hosted: `{entry['hosted']}` | Co-hosted: `{entry['cohosted']}` | Total: **{entry['total']}**\n\n"
            )

        embed = self.bot.format_embed(self.bot.config, 'staff_leaderboard', entries=description)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Staff(bot))