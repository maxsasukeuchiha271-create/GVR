import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal

class HireRoleSelect(discord.ui.Select):
    def __init__(self, target_user: discord.Member):
        self.target_user = target_user
        options = [
            discord.SelectOption(label="Junior Associate", value="1474657477923569674", description="Assign Low Command Role"),
            discord.SelectOption(label="Server Associate", value="1474657421413711872", description="Assign Low Command Role"),
            discord.SelectOption(label="Senior Associate", value="1474657432381685883", description="Assign Middle Command Role"),
            discord.SelectOption(label="Lead Associate", value="1474657287493914635", description="Assign Middle Command Role"),
        ]
        super().__init__(placeholder="Select a staff rank for the new staff member...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        
        if role:
            await self.target_user.add_roles(role)
            
            embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Legacy_ - ___Hiring___ <a:recolored_recolored_red_stars:1499985951894802553>",
                description=f"> <a:recolored_arrowmove:1499985868541133038>  Successfully assigned {role.mention} to {self.target_user.mention}.",
                color=0xadcf8b
            )
            embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])
            
            # Disable the select menu after use
            self.disabled = True
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            await interaction.response.send_message("Role not found.", ephemeral=True)

class HireView(discord.ui.View):
    def __init__(self, target_user: discord.Member):
        super().__init__(timeout=60)
        self.add_item(HireRoleSelect(target_user))

class Hire(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hire", description="Hire a new staff member")
    @app_commands.describe(user="The user to hire", rank="The staff rank to assign", reason="Reason for hiring")
    async def hire(self, interaction: discord.Interaction, user: discord.Member, rank: Literal["Junior Associate", "Server Associate", "Senior Associate", "Lead Associate"], reason: str):
        # Allowed roles to use the command: Council (1452886793278984315) & Executive (1474531421073969182)
        hc_id = int(self.bot.config['roles']['high_command'])
        overseer_id = int(self.bot.config['roles']['overseer'])
        
        ALLOWED_ROLES = [hc_id, overseer_id]
        STAFF_ROLE_ID = 1474665732133486592

        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to hire staff.", ephemeral=True)

        # Give the base staff role
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            await user.add_roles(staff_role)
        else:
            return await interaction.response.send_message("Staff role not found in server.", ephemeral=True)

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Staff Hire___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=(
                f"> <a:recolored_arrowmove:1499985868541133038>  **__User:__** {user.mention}\n"
                f"> <a:recolored_arrowmove:1499985868541133038>  **__Hired By:__** {interaction.user.mention}\n"
                f"> <a:recolored_arrowmove:1499985868541133038>  **__Rank:__** {rank}\n"
                f"> <a:recolored_arrowmove:1499985868541133038>  **__Reason:__** {reason}\n\n"
                "Please select the staff rank for the new staff member below."
            ),
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

        view = HireView(user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Log the hire
        log_channel_id = 1474542725775753216
        if log_channel_id:
            channel = interaction.guild.get_channel(log_channel_id)
            if channel:
                log_embed = discord.Embed( 
                    title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Staff Hire Log___ <a:recolored_recolored_red_stars:1499985951894802553>",
                    description=(
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__User:__** {user.mention} ({user.id})\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Moderator:__** {interaction.user.mention}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Rank:__** {rank}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Reason:__** {reason}"
                    ),
                    color=0xadcf8b,
                    timestamp=discord.utils.utcnow()
                )
                log_embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])
                await channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(Hire(bot))
