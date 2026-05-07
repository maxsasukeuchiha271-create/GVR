import discord
from discord import app_commands
from discord.ext import commands

class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        ALLOWED_BAN_ROLES_IDS = [1474654932182503536, 1474654744487395488]
        if not any(r.id in ALLOWED_BAN_ROLES_IDS for r in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to unban users.", ephemeral=True)

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
        except Exception as e:
            return await interaction.response.send_message(f" Error unbanning: {e}", ephemeral=True)

        log_channel_id = interaction.client.config['channels'].get('mod_logs_channel_id')
        if log_channel_id:
            channel = interaction.guild.get_channel(int(log_channel_id))
            if channel:
                log_embed = discord.Embed( 
                    title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Unban Log___ <a:recolored_recolored_red_stars:1499985951894802553>",
                    description=f"> <a:recolored_arrowmove:1499985868541133038>  **__User:__** {user} ({user.id})\n> <a:recolored_arrowmove:1499985868541133038>  **__Moderator:__** {interaction.user.mention}",
                    color=0xadcf8b,
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])
                await channel.send(embed=log_embed)

        final_embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Success___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  Successfully unbanned **{user}** from the server.",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        final_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

        await interaction.response.send_message(embed=final_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Unban(bot))