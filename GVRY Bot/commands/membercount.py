import discord
from discord import app_commands
from discord.ext import commands

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="membercount", description="View the server's member count and statistics")
    async def membercount(self, interaction: discord.Interaction):
        await interaction.response.send_message("Fetching server statistics...", ephemeral=True)
        
        guild = interaction.guild
        
        # Basic counts
        total = guild.member_count

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Legacy_ - ___Member Count___ <a:recolored_recolored_red_stars:1499985951894802553>",
            color=0xadcf8b,
            timestamp=discord.utils.utcnow()
        )
        
        arrow = "<a:recolored_arrowmove:1499985868541133038>"
        stars = "<a:recolored_recolored_red_stars:1499985951894802553>"
        
        embed.description = f"> {arrow} Greenville Roleplay Legacy has hit **{total}** Members! Thank you all for being a part of the community {stars}"
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))
