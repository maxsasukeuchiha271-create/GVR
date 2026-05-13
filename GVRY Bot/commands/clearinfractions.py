import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from database import Database

class ClearInfractions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clearinfractions", description="Clear infractions from a user")
    @app_commands.describe(user="The user to clear infractions from", infraction_id="The ID of the infraction to remove", reason="Reason for clearing")
    async def clearinfractions(self, interaction: discord.Interaction, user: discord.Member, infraction_id: str, reason: str):
        if 1474665732133486592 not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Only staff team members can use this command.", ephemeral=True)

        uid = str(user.id)
        infraction = await Database.fetch_one("SELECT * FROM moderation WHERE id = ? AND user_id = ? AND type = 'infraction' AND cleared = 0", (infraction_id, uid))

        if not infraction:
            return await interaction.response.send_message("Invalid Infraction ID or already cleared.", ephemeral=True)

        await Database.execute(
            "UPDATE moderation SET cleared = 1, cleared_by = ?, cleared_reason = ? WHERE id = ?",
            (str(interaction.user.id), reason, infraction_id)
        )

        roles_config = interaction.client.config['roles']
        INF_ROLES = [
            int(roles_config['infraction_1']),
            int(roles_config['infraction_2']),
            int(roles_config['infraction_3'])
        ]
        active_res = await Database.fetch_all("SELECT id FROM moderation WHERE user_id = ? AND type = 'infraction' AND cleared = 0", (uid,))
        new_count = len(active_res)
        
        for role_id in INF_ROLES:
            role = interaction.guild.get_role(role_id)
            if role and role in user.roles:
                await user.remove_roles(role)
        
        for i in range(min(new_count, len(INF_ROLES))):
            role = interaction.guild.get_role(INF_ROLES[i])
            if role: await user.add_roles(role)

        embed = discord.Embed(
            title="<a:BlueButterflies:1497980075008852028> _Greenville Roleplay Legacy_ - ___Infraction Cleared___ <a:BlueButterflies:1497980075008852028>",
            description=f"> <a:BlueButterflies:1497980075008852028>  **__User:__** {user.mention}\n> <a:BlueButterflies:1497980075008852028>  **__Infraction ID:__** `{infraction_id.upper()}`\n> <a:BlueButterflies:1497980075008852028>  **__Reason:__** {reason}",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @clearinfractions.autocomplete('infraction_id')
    async def inf_autocomplete(self, interaction: discord.Interaction, current: str):
        user = interaction.namespace.user
        if not user: return []
        active_infs = await Database.fetch_all("SELECT id, reason FROM moderation WHERE user_id = ? AND type = 'infraction' AND cleared = 0", (str(user.id),))
        return [app_commands.Choice(name=f"{inf['id']} - {inf['reason'][:20]}", value=inf['id']) for inf in active_infs if current.lower() in inf['id'].lower()][:25]

async def setup(bot):
    await bot.add_cog(ClearInfractions(bot))
