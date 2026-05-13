import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from database import Database

class ClearStrikes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clearstrikes", description="Clear staff strikes from a user's profile")
    @app_commands.describe(user="The staff member to clear strikes from", strike_id="The ID of the strike to remove", reason="Reason for clearing")
    async def clearstrikes(self, interaction: discord.Interaction, user: discord.Member, strike_id: str, reason: str):
        # Specific roles allowed to use this command
        hc_id = int(interaction.client.config['roles']['high_command'])
        overseer_id = int(interaction.client.config['roles']['overseer'])
        if not any(role.id in [hc_id, overseer_id] for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to clear staff strikes.", ephemeral=True)

        uid = str(user.id)
        # Check if strike exists and is active
        strike = await Database.fetch_one("SELECT * FROM moderation WHERE id = ? AND user_id = ? AND type = 'strike' AND cleared = 0", (strike_id, uid))

        if not strike:
            return await interaction.response.send_message("Invalid Strike ID or already cleared.", ephemeral=True)

        # Mark as cleared in DB
        await Database.execute(
            "UPDATE moderation SET cleared = 1, cleared_by = ?, cleared_reason = ? WHERE id = ?",
            (str(interaction.user.id), reason, strike_id)
        )

        # Staff Strike Roles to manage
        roles_config = interaction.client.config['roles']
        STRK_ROLES = [
            int(roles_config['strike_1']),
            int(roles_config['strike_2']),
            int(roles_config['strike_3'])
        ]
        active_strikes = await Database.fetch_all("SELECT id FROM moderation WHERE user_id = ? AND type = 'strike' AND cleared = 0", (uid,))
        new_count = len(active_strikes)
        
        # Remove all strike roles first
        for role_id in STRK_ROLES:
            role = interaction.guild.get_role(role_id)
            if role and role in user.roles:
                await user.remove_roles(role)
        
        # Re-add roles based on new count
        for i in range(min(new_count, len(STRK_ROLES))):
            role = interaction.guild.get_role(STRK_ROLES[i])
            if role: await user.add_roles(role)

        embed = discord.Embed(
            title="<a:BlueButterflies:1497980075008852028> _Greenville Roleplay Legacy_ - ___Staff Strike Cleared___ <a:BlueButterflies:1497980075008852028>",
            description=f"> <a:BlueButterflies:1497980075008852028>  **__User:__** {user.mention}\n> <a:recolored_arrowmove:1499985868541133038>  **__Strike ID:__** `{strike_id.upper()}`\n> <a:BlueButterflies:1497980075008852028>  **__Reason:__** {reason}",
            color=0x8d021f,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @clearstrikes.autocomplete('strike_id')
    async def strike_autocomplete(self, interaction: discord.Interaction, current: str):
        user = interaction.namespace.user
        if not user: return []
        
        active_strikes = await Database.fetch_all("SELECT id, reason FROM moderation WHERE user_id = ? AND type = 'strike' AND cleared = 0", (str(user.id),))
        
        return [app_commands.Choice(name=f"{s['id']} - {s['reason'][:20]}", value=s['id']) for s in active_strikes if current.lower() in s['id'].lower()][:25]

async def setup(bot):
    await bot.add_cog(ClearStrikes(bot))
