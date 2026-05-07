import discord
from discord import app_commands
from discord.ext import commands
from database import Database

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register", description="Register a vehicle with your profile")
    @app_commands.describe(
        year="Vehicle year (e.g., 2023)",
        make="Vehicle make/brand (e.g., Toyota)",
        model="Vehicle model (e.g., Camry)",
        color="Vehicle color (e.g., Blue)",
        plate="License plate number (e.g., ABC123)"
    )
    async def register(
        self,
        interaction: discord.Interaction,
        year: str,
        make: str,
        model: str,
        color: str,
        plate: str
    ):
        user_id = str(interaction.user.id)

        # Check for duplicate plate across the whole server
        duplicate = await Database.fetch_one("SELECT id FROM vehicles WHERE plate = ?", (plate,))
        if duplicate:
            return await interaction.response.send_message(
                f" A vehicle with the license plate `{plate.upper()}` is already registered.",
                ephemeral=True
            )

        # Add new vehicle to DB
        await Database.execute(
            "INSERT INTO vehicles (user_id, year, make, model, color, plate) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, year, make, model, color, plate)
        )

        embed_color = 0xadcf8b

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Vehicle Registered___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  Your vehicle has been successfully registered to your profile!\n\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Year:__** {year}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Make:__** {make}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Model:__** {model}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__Color:__** {color}\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  **__License Plate:__** `{plate.upper()}`",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Register(bot))
