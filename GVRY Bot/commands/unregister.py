import discord
from discord import app_commands
from discord.ext import commands
from database import Database

class Unregister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="unregister", description="Unregister a vehicle from your profile using the license plate")
    @app_commands.describe(plate="The license plate of the vehicle to remove")
    async def unregister(self, interaction: discord.Interaction, plate: str):
        user_id = str(interaction.user.id)

        # Find the vehicle with the matching plate and user
        vehicle = await Database.fetch_one(
            "SELECT id FROM vehicles WHERE user_id = ? AND plate = ?", 
            (user_id, plate)
        )

        if not vehicle:
            await interaction.response.send_message(f" No vehicle found with the license plate `{plate}`.", ephemeral=True)
            return

        await Database.execute("DELETE FROM vehicles WHERE id = ?", (vehicle['id'],))

        embed_color = 0xadcf8b

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Vehicle Unregistered___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  The vehicle with license plate `{plate.upper()}` has been successfully removed from your profile.",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Unregister(bot))
