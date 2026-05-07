import discord
import asyncio
from discord import app_commands
from discord.ext import commands

DEFAULT_STAFF_ROLE_ID = 1474665732133486592

def _ticket_cfg(client):
    return client.config.get('tickets', {})

def _staff_role_id(client):
    cfg = _ticket_cfg(client)
    return int(cfg.get('staff_role_id', DEFAULT_STAFF_ROLE_ID))

def _type_cfg(client, ticket_type):
    types = _ticket_cfg(client).get('types', {})
    return types.get(ticket_type, {})

async def get_ticket_opener(channel: discord.TextChannel):
    topic = channel.topic or ""
    if "Opener ID: " in topic:
        try:
            user_id = int(topic.split("Opener ID: ")[1])
            return channel.guild.get_member(user_id) or await channel.guild.fetch_member(user_id)
        except Exception:
            return None
    return None

async def get_ticket_claimer(channel: discord.TextChannel, opener_id: int, staff_role_id: int):
    staff_role = channel.guild.get_role(staff_role_id)
    if not staff_role or channel.overwrites_for(staff_role).send_messages is not False:
        return None
    for target, overwrite in channel.overwrites.items():
        if isinstance(target, discord.Member) and not target.bot and target.id != opener_id:
            if overwrite.send_messages is True:
                return target
    return None

async def close_ticket_internal(interaction: discord.Interaction, reason: str):
    opener = await get_ticket_opener(interaction.channel)
    sid = _staff_role_id(interaction.client)
    claimer = await get_ticket_claimer(interaction.channel, opener.id if opener else 0, sid)

    embed = discord.Embed(
        title="<a:recolored_recolored_red_stars:1499985951894802553> Ticket Closed",
        description=f"Your ticket in **{interaction.guild.name}** has been closed.",
        color=0xadcf8b,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
    embed.add_field(name="Claimed By", value=claimer.mention if claimer else "Not Claimed", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(
        text=interaction.client.config['bot']['footer_text'],
        icon_url=interaction.client.config['bot']['footer_icon']
    )

    if opener:
        try:
            await opener.send(embed=embed)
        except Exception:
            pass

    msg = "This ticket will be closed and deleted in 5 seconds..."
    if interaction.response.is_done():
        await interaction.followup.send(msg)
    else:
        await interaction.response.send_message(msg)

    await asyncio.sleep(5)
    await interaction.channel.delete()


class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Yes, Close Ticket", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await close_ticket_internal(interaction, "No reason provided (Closed via confirmation button)")


class TicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        sid = _staff_role_id(interaction.client)
        if sid not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("Only staff team members can claim tickets.", ephemeral=True)

        staff_role = interaction.guild.get_role(sid)
        is_claimed = staff_role and interaction.channel.overwrites_for(staff_role).send_messages is False

        if not is_claimed:
            opener = await get_ticket_opener(interaction.channel)
            button.label = "Unclaim Ticket"
            button.style = discord.ButtonStyle.secondary
            await interaction.channel.set_permissions(staff_role, view_channel=True, send_messages=False, read_message_history=True)
            await interaction.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
            if opener:
                await interaction.channel.set_permissions(opener, view_channel=True, send_messages=True, read_message_history=True)
            embed = discord.Embed(
                title="<a:recolored_recolored_red_stars:1499985951894802553> Ticket Claimed",
                description=(
                    f"> <a:recolored_arrowmove:1499985868541133038>  Your ticket is now being handled by {interaction.user.mention}.\n"
                    f"> <a:recolored_arrowmove:1499985868541133038>  Other staff members have been restricted from speaking in this channel."
                ),
                color=0xadcf8b
            )
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(embed=embed)
        else:
            button.label = "Claim Ticket"
            button.style = discord.ButtonStyle.primary
            await interaction.channel.set_permissions(staff_role, view_channel=True, send_messages=True, read_message_history=True)
            opener = await get_ticket_opener(interaction.channel)
            for target, overwrite in interaction.channel.overwrites.items():
                if isinstance(target, discord.Member) and not target.bot:
                    if opener and target.id == opener.id:
                        continue
                    if overwrite.send_messages is True:
                        await interaction.channel.set_permissions(target, overwrite=None)
            embed = discord.Embed(
                title="Ticket Unclaimed",
                description=(
                    f"> <a:recolored_arrowmove:1499985868541133038>  {interaction.user.mention} has unclaimed this ticket.\n"
                    f"> <a:recolored_arrowmove:1499985868541133038>  All staff members can now respond to this ticket."
                ),
                color=0xadcf8b
            )
            await interaction.response.edit_message(view=self)
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        opener = await get_ticket_opener(interaction.channel)
        sid = _staff_role_id(interaction.client)
        is_staff = sid in [role.id for role in interaction.user.roles]
        is_opener = opener and interaction.user.id == opener.id

        if not is_staff and not is_opener:
            return await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)

        embed = discord.Embed(
            title="Close Confirmation",
            description="Are you sure you want to close this ticket? This action cannot be undone.",
            color=0xadcf8b
        )
        await interaction.response.send_message(embed=embed, view=CloseConfirmView(), ephemeral=True)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, bot_config):
        options = []
        types = bot_config.get('tickets', {}).get('types', {})
        for key, val in types.items():
            emoji_val = val.get('emoji')
            # Basic validation: If it's text without emoji characters or custom formatting, ignore it to prevent 400 errors
            if emoji_val and not (emoji_val.startswith('<') or any(ord(c) > 127 for c in emoji_val)):
                emoji_val = None

            options.append(discord.SelectOption(
                label=val.get('label', key),
                value=key,
                description=val.get('description', ''),
                emoji=emoji_val
            ))
        super().__init__(placeholder="Select a ticket category...", min_values=1, max_values=1, options=options or [discord.SelectOption(label="None", value="none")], custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        await interaction.response.defer(ephemeral=True)

        tcfg = _ticket_cfg(interaction.client)
        sid = int(tcfg.get('staff_role_id', DEFAULT_STAFF_ROLE_ID))
        category_id = int(tcfg.get('category_id', 0))
        type_cfg = _type_cfg(interaction.client, ticket_type)

        channel_name = f"{ticket_type}-{user.name}"
        staff_role = guild.get_role(sid)
        category = guild.get_channel(category_id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, create_public_threads=False,
                create_private_threads=False, send_messages_in_threads=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, create_public_threads=False,
                create_private_threads=False, send_messages_in_threads=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                embed_links=True, manage_channels=True, manage_threads=True
            )
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                create_public_threads=False, create_private_threads=False, send_messages_in_threads=False
            )

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Ticket Type: {type_cfg.get('label', ticket_type)} | Opener ID: {user.id}"
        )

        # Use unified embed keys: ticket_welcome_general, ticket_welcome_civilian, etc.
        embed_key = f"ticket_welcome_{ticket_type}"
        welcome_embed = interaction.client.format_embed(
            interaction.client.config, embed_key, user=user.mention
        )
        view = TicketActionsView()
        await ticket_channel.send(
            content=f"@everyone {user.mention} | {staff_role.mention if staff_role else ''}",
            embed=welcome_embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True)
        )

        await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self, bot_config):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect(bot_config))


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="close", description="Close the current ticket with an optional reason")
    @app_commands.describe(reason="The reason for closing this ticket")
    async def close(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        opener = await get_ticket_opener(interaction.channel)
        if not opener:
            return await interaction.response.send_message("This command can only be used in a ticket channel.", ephemeral=True)

        sid = _staff_role_id(interaction.client)
        is_staff = sid in [role.id for role in interaction.user.roles]
        is_opener = interaction.user.id == opener.id

        if not is_staff and not is_opener:
            return await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)

        await close_ticket_internal(interaction, reason)

    @app_commands.command(name="sendticketpanel", description="Send the ticket creation panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def sendticketpanel(self, interaction: discord.Interaction):
        embed = self.bot.format_embed(self.bot.config, 'ticket_panel')
        
        # Determine target channel
        cfg = _ticket_cfg(self.bot)
        target_id = cfg.get('panel_channel_id')
        target_channel = self.bot.get_channel(int(target_id)) if target_id else interaction.channel
        
        if not target_channel:
             return await interaction.response.send_message(f"Error: Could not find channel with ID `{target_id}`.", ephemeral=True)

        await target_channel.send(embed=embed, view=TicketPanelView(self.bot.config))
        await interaction.response.send_message(f"Ticket panel sent to {target_channel.mention}.", ephemeral=True)

    @sendticketpanel.error
    async def sendticketpanel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Only Administrators can use this command.", ephemeral=True)


async def setup(bot):
    # Note: TicketPanelView is dynamic, persistence is handled manually if needed
    bot.add_view(TicketActionsView())
    await bot.add_cog(Tickets(bot))
