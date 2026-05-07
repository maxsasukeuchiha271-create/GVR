import discord
from discord.ext import commands
from discord import app_commands
import datetime
import re
import json
from pathlib import Path

class ModerationPlus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, duration_str: str):
        if not duration_str:
            return None
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        # Match digits followed by a unit (s, m, h, d)
        match = re.match(r"(\d+)([smhd])", duration_str.lower())
        if not match:
            return None
        amount, unit = match.groups()
        return datetime.timedelta(seconds=int(amount) * units[unit])

    @commands.hybrid_command(name="mute", description="Mute (timeout) a member")
    @app_commands.describe(member="The user to mute", length="Duration (e.g. 10m, 1h, 1d)", reason="Optional reason")
    @app_commands.guild_only()
    async def mute(self, ctx: commands.Context, member: discord.Member, length: str, *, reason: str = "No reason provided"):
        staff_role_id = int(self.bot.config['roles']['staff_team'])
        if staff_role_id not in [role.id for role in ctx.author.roles]:
            await ctx.send("Only staff team members can use this command.", ephemeral=True if ctx.interaction else None)
            return

        duration = self.parse_duration(length)
        if not duration:
            await ctx.send("Invalid duration format. Use e.g. 10m, 1h, 1d.", ephemeral=True if ctx.interaction else None)
            return

        # Discord timeout limit is 28 days
        if duration > datetime.timedelta(days=28):
            await ctx.send("Maximum timeout duration is 28 days.", ephemeral=True if ctx.interaction else None)
            return

        try:
            await member.timeout(duration, reason=reason)
            
            # Attempt to DM the user about the mute
            try:
                dm_embed = discord.Embed(
                    title=f"Muted in {ctx.guild.name}",
                    description=f"You have been muted for `{length}`.\n**Reason:** {reason}",
                    color=0xadcf8b
                )
                dm_embed.set_footer(text=self.bot.config['bot']['footer_text'], icon_url=self.bot.config['bot']['footer_icon'])
                await member.send(embed=dm_embed)
            except:
                pass

            embed = discord.Embed(
                title="Member Muted",
                description=f"{member.mention} has been muted for `{length}`.\n**Reason:** {reason}",
                color=0xadcf8b
            )
            embed.set_footer(text=self.bot.config['bot']['footer_text'], icon_url=self.bot.config['bot']['footer_icon'])
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I do not have permission to timeout this member.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name="unmute")
    @commands.guild_only()
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        staff_role_id = int(self.bot.config['roles']['staff_team'])
        if staff_role_id not in [role.id for role in ctx.author.roles]:
            await ctx.send("Only staff team members can use this command.")
            return

        try:
            await member.timeout(None, reason=reason)
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"Successfully unmuted {member.mention}.\n**Reason:** {reason}",
                color=0xadcf8b
            )
            embed.set_footer(text=self.bot.config['bot']['footer_text'], icon_url=self.bot.config['bot']['footer_icon'])
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I do not have permission to unmute this member.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @app_commands.command(name="prefix", description="Change the bot's prefix (Admin only)")
    @app_commands.describe(new_prefix="The new prefix to use")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def prefix(self, interaction: discord.Interaction, new_prefix: str):
        self.bot.config['bot']['prefix'] = new_prefix
        
        # Save to config.json using the base_dir stored in bot
        config_path = self.bot.base_dir / 'config.json'
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.bot.config, f, indent=2)
            await interaction.response.send_message(f"Prefix has been changed to `{new_prefix}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error saving prefix: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationPlus(bot))