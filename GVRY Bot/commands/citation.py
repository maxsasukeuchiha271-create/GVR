import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
import uuid
from datetime import datetime
from database import Database

class PayCitationView(discord.ui.View):
    def __init__(self, target_user_id: int, citation_id: str):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.citation_id = citation_id

    @discord.ui.button(label="Pay Citation", style=discord.ButtonStyle.success, custom_id="pay_citation_button")
    async def pay_citation(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer immediately to prevent "Interaction failed" timeout while processing database calls
        await interaction.response.defer(ephemeral=True)

        # Fetch citation from DB to verify existence, recipient, price, and message_id
        citation = await Database.fetch_one("SELECT user_id, price, message_id FROM citations WHERE id = ?", (self.citation_id,))
        
        if not citation:
            return await interaction.followup.send("Citation record not found or already paid.", ephemeral=True)
            
        # Verify the person clicking is the person cited
        if interaction.user.id != int(citation['user_id']):
            return await interaction.followup.send("Only the person this citation is issued to can pay it.", ephemeral=True)

        price = citation['price']
        user_id_str = str(interaction.user.id)
        user_econ = await Database.fetch_one("SELECT wallet FROM economy WHERE user_id = ?", (user_id_str,))

        if not user_econ or user_econ['wallet'] < price:
            return await interaction.followup.send(f"You do not have enough money in your wallet to pay this citation. You need **${price:,}**.", ephemeral=True)

        # Update economy and remove citation
        await Database.execute("UPDATE economy SET wallet = wallet - ? WHERE user_id = ?", (price, user_id_str))
        await Database.execute("DELETE FROM citations WHERE id = ?", (self.citation_id,))

        # Update the button appearance
        button.disabled = True
        button.label = "Paid"
        button.style = discord.ButtonStyle.secondary
        
        # Update the message where the button was clicked
        try:
            await interaction.edit_original_response(view=self)
        except:
            pass

        # Update the log message in the citation logs channel if it exists
        if citation['message_id']:
            try:
                log_channel_id = int(interaction.client.config['channels']['citation_logs_channel_id'])
                log_channel = interaction.client.get_channel(log_channel_id)
                log_msg = await log_channel.fetch_message(int(citation['message_id']))
                await log_msg.edit(view=self)
            except: pass

        await interaction.followup.send(f"You have successfully paid citation **{self.citation_id}** for **${price:,}**.", ephemeral=True)
        try:
            await interaction.user.send(f"Your citation **{self.citation_id}** has been paid and removed from your profile.")
        except discord.Forbidden:
            pass

class Citation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="citation", description="Issue a citation to a user")
    @app_commands.describe(
        user="The user receiving the citation",
        department="The department issuing the citation",
        reason="The reason for the citation",
        penal_code="The penal code for the violation",
        price="The fine amount for the citation",
        make="Vehicle Make (e.g. Toyota)",
        model="Vehicle Model (e.g. Camry)",
        colour="Vehicle Color",
        plate="License Plate"
    )
    async def citation(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member, 
        department: Literal["Wisconsin State Patrol", "Outagamie County Sheriff", "Fox Valley Metro Police Department"], 
        reason: str,
        penal_code: str,
        price: int,
        make: str,
        model: str,
        colour: str,
        plate: str
    ):
        allowed_roles = interaction.client.config.get('permissions', {}).get('citation', [])
        if not any(role.id in [int(r) for r in allowed_roles] for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        citation_id = f"GVRY-{uuid.uuid4().hex[:6].upper()}"
        
        try:
            LOG_CHANNEL_ID = int(interaction.client.config['channels']['citation_logs_channel_id'])
            embed_color = 0xadcf8b
            footer_text = interaction.client.config['bot']['footer_text']
            footer_icon = interaction.client.config['bot']['footer_icon']
        except:
            LOG_CHANNEL_ID = 1499610268873789502
            embed_color = 0xadcf8b
            footer_text = "Greenville Roleplay Yowe"
            footer_icon = None
        
        embed = discord.Embed(
            title="Citation Issued",
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Recipient", value=user.mention, inline=True)
        embed.add_field(name="Officer", value=interaction.user.mention, inline=True)
        embed.add_field(name="Citation ID", value=f"`{citation_id}`", inline=True)
        embed.add_field(name="Department", value=department, inline=True)
        embed.add_field(name="Penal Code", value=penal_code, inline=True)
        embed.add_field(name="Fine", value=f"${price:,}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Vehicle", value=f"{make} {model} ({colour}) — `{plate.upper()}`", inline=False)
        embed.set_author(name=f"Issued by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=footer_text, icon_url=footer_icon)

        # Added a banner image to stretch the embed to full width and give it a professional look
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            view = PayCitationView(user.id, citation_id)
            log_message = await log_channel.send(content=user.mention, embed=embed, view=view)
            
            # Save to Database BEFORE sending to the user to avoid race condition
            await Database.execute(
                "INSERT INTO citations (id, user_id, department, reason, penal_code, price, officer_id, status, message_id, vehicle_make, vehicle_model, vehicle_color, vehicle_plate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (citation_id, str(user.id), department, reason, penal_code, price, str(interaction.user.id), "Unpaid", str(log_message.id), make, model, colour, plate)
            )

            try:
                await user.send(content="**You have received a citation.**", embed=embed, view=PayCitationView(user.id, citation_id))
            except discord.Forbidden:
                pass
            
            await interaction.response.send_message(f"Citation issued and logged to <#{LOG_CHANNEL_ID}>.", ephemeral=True)
        else:
            await interaction.response.send_message("Citation log channel not found.", ephemeral=True)

    @app_commands.command(name="clearcitation", description="Remove citations from a user's profile")
    async def clear_citation(self, interaction: discord.Interaction, user: discord.Member, citation_id: str, reason: str):
        allowed_roles = interaction.client.config.get('permissions', {}).get('clearcitation', [])
        if not any(role.id in [int(r) for r in allowed_roles] for role in interaction.user.roles):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        user_id_str = str(user.id)
        citation = await Database.fetch_one("SELECT * FROM citations WHERE id = ? AND user_id = ?", (citation_id, user_id_str))

        if not citation:
            return await interaction.response.send_message(f"No citation found with ID `{citation_id}` for {user.display_name}.", ephemeral=True)

        await Database.execute("DELETE FROM citations WHERE id = ?", (citation_id,))
        
        await interaction.response.send_message(f"Cleared citation `{citation_id}`.", ephemeral=True)
        try:
            await user.send(f"Citation `{citation_id}` removed from your profile.\n**Reason:** {reason}")
        except discord.Forbidden:
            pass

    @clear_citation.autocomplete('citation_id')
    async def citation_id_autocomplete(self, interaction: discord.Interaction, current: str):
        user = interaction.namespace.user
        if not user:
            return []
        
        user_id_str = str(user.id)
        user_citations = await Database.fetch_all("SELECT id FROM citations WHERE user_id = ? AND status = 'Unpaid'", (user_id_str,))
        
        return [app_commands.Choice(name=c['id'], value=c['id']) for c in user_citations if current.lower() in c['id'].lower()][:25]

async def setup(bot):
    await bot.add_cog(Citation(bot))