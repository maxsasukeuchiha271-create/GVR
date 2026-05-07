import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Dict, Any
from database import Database

class VehicleButton(discord.ui.Button):
    def __init__(self, user):
        super().__init__(label="View Registered Cars", style=discord.ButtonStyle.primary)
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        # Defer to prevent timeout during DB fetch
        await interaction.response.defer(ephemeral=False)

        user_id = str(self.user.id)
        vehicles = await Database.fetch_all(
            "SELECT * FROM vehicles WHERE user_id = ?", (user_id,)
        )

        embed_color = 0xadcf8b

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___Registered Vehicles___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=f"**Profile:** {self.user.mention}",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )

        # Get vehicles registered
        if vehicles:
            vehicle_count = len(vehicles)

            embed.add_field(
                name="<a:recolored_arrowmove:1499985868541133038>  Total Vehicles Registered",
                value=f"`{vehicle_count}`",
                inline=True
            )

            # Display each vehicle
            for idx, vehicle in enumerate(vehicles, 1):
                vehicle_info = (
                    f"**Year:** {vehicle['year']}\n"
                    f"**Make:** {vehicle['make']}\n"
                    f"**Model:** {vehicle['model']}\n"
                    f"**Color:** {vehicle['color']}\n"
                    f"**Plate:** `{vehicle['plate']}`"
                )
                embed.add_field(
                    name=f" Vehicle {idx}",
                    value=vehicle_info,
                    inline=False
                )
        else:
            embed.description += "\n\n No vehicles registered yet."
            embed.add_field(
                name="<a:recolored_arrowmove:1499985868541133038>  To Register a Vehicle",
                value="Please use the `/register` command",
                inline=False
            )

        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.followup.send(embed=embed, ephemeral=False)


class ViewCitationsButton(discord.ui.Button):
    def __init__(self, user: discord.User):
        super().__init__(label="View Citations", style=discord.ButtonStyle.secondary, custom_id="view_citations_button")
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        user_id_str = str(self.user.id)
        user_citations = await Database.fetch_all("SELECT * FROM citations WHERE user_id = ?", (user_id_str,))

        if not user_citations:
            return await interaction.followup.send(" You have no citations on record.", ephemeral=False)

        embed_color = 0xadcf8b

        try:
            log_channel_id = int(interaction.client.config['channels']['citation_logs_channel_id'])
        except (KeyError, ValueError):
            # Fallback to the ID provided in your citation command if config fails
            log_channel_id = 1499610268873789502

        embed = discord.Embed(
            title="<:GVRY_pfp:1500241318465638601>  _Greenville Roleplay Yowe_ - __Your Citations___",
            description=f"**Profile:** {self.user.mention}\n\n",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )

        for citation in user_citations:
            citation_id = citation["id"]
            department = citation["department"]
            reason = citation["reason"]
            penal_code = citation["penal_code"]
            price = citation["price"]
            status = citation["status"]
            message_id = citation["message_id"]

            citation_link = "N/A (Message not found or not logged)"
            if message_id:
                # Construct the Discord message link
                citation_link = f"[View Citation Message](https://discord.com/channels/{interaction.guild.id}/{log_channel_id}/{message_id})"

            embed.add_field(
                name=f"**__Citation ID:__** {citation_id} ({status})",
                value=(
                    f"**Department:** {department}\n"
                    f"**Reason:** {reason}\n"
                    f"**Penal Code:** {penal_code}\n"
                    f"**Fine:** ${price:,}\n"
                    f"{citation_link}"
                ),
                inline=False
            )
        
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        await interaction.followup.send(embed=embed, ephemeral=False)


class ProfileActionsView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.add_item(VehicleButton(user))
        self.add_item(ViewCitationsButton(user))

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View your civilian profile with registered vehicles")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        user_id = str(interaction.user.id)

        roblox_id = None
        roblox_user = "Not Linked"

        try:
            # Replace JSON reading with DB queries
            vehicle_count = await Database.get_vehicle_count(user_id) or 0
            citation_count = await Database.get_citation_count(user_id) or 0

            # Fetch Roblox info from DB
            econ_res = await Database.fetch_one("SELECT roblox_id, roblox_username FROM economy WHERE user_id = ?", (user_id,))
            if econ_res:
                roblox_id = econ_res.get('roblox_id')
                roblox_user = econ_res.get('roblox_username') or "Not Linked"
            
            # ALWAYS attempt to auto-verify to ensure roles and profile are synced
            info = await self.bot.verify_user(interaction.user)
            if info:
                roblox_id = info['roblox_id']
                roblox_user = info['username']

        except Exception:
            vehicle_count = 0
            citation_count = 0

        roblox_display = f"[{roblox_user}](https://www.roblox.com/users/{roblox_id}/profile)" if roblox_id else "`Not Linked`"
        embed_color = 0xadcf8b

        description = (
            f"**Member Profile:** {interaction.user.mention}\n\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **Roblox Profile:** {roblox_display}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **Vehicles Registered:** `{vehicle_count}`\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **Total Citations:** `{citation_count}`\n\n"
            f"*Use `/register` to add a new vehicle to your profile.*"
        )

        embed = discord.Embed(
            title="<a:recolored_recolored_red_stars:1499985951894802553> Greenville Roleplay Yowe - Civilian Profile <a:recolored_recolored_red_stars:1499985951894802553>",
            description=description,
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        view = ProfileActionsView(interaction.user)
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Profile(bot))
