import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from utils import format_embed
from database import Database

async def startup_required(interaction: discord.Interaction) -> bool:
    states = getattr(interaction.client, 'session_states', {})
    if not states.get(interaction.channel_id, {}).get('completed'):
        await interaction.response.send_message(
            " You must use the `/startup` command in this channel before using other commands.", ephemeral=True
        )
        return False
    return True

async def correct_channel(interaction: discord.Interaction) -> bool:
    channels = interaction.client.config['channels']
    id1 = channels.get('session_commands_channel_id')
    id2 = channels.get('session_commands_channel_id_2')
    if str(interaction.channel_id) not in [str(id1), str(id2)]:
        await interaction.response.send_message(
            f" This command can only be used in <#{id1}> or <#{id2}>.", ephemeral=True
        )
        return False
    return True

def _embed_cfg(bot, key):
    return bot.config.get('embeds', {}).get(key, {})

class SessionButton(discord.ui.View):
    def __init__(self, session_link: str):
        super().__init__(timeout=None)
        self.session_link = session_link

    @discord.ui.button(label="Session link", style=discord.ButtonStyle.primary)
    async def send_link(self, interaction: discord.Interaction, _button: discord.ui.Button):
        states = getattr(interaction.client, 'session_states', {})
        state = states.get(interaction.channel_id, {})
        if interaction.user.id not in state.get('reactors', set()):
            guild_id = interaction.guild.id
            msg_id = state.get('message_id')
            link = f"https://discord.com/channels/{guild_id}/{interaction.channel_id}/{msg_id}"
            return await interaction.response.send_message(
                f"__You Must React To The [Startup Message]({link}) To Get Access To This Session__",
                ephemeral=True
            )

        # Group Lock Logic
        blox_cfg = interaction.client.config.get('bloxlinks', {})
        if blox_cfg.get('group_lock_active'):
            await interaction.response.defer(ephemeral=True)
            
            # Try DB first for speed/reliability
            res = await Database.fetch_one("SELECT roblox_id FROM economy WHERE user_id = ?", (str(interaction.user.id),))
            roblox_id = res.get('roblox_id') if res else None
            
            if not roblox_id:
                info = await interaction.client.fetch_roblox_info(interaction.user.id)
                if info:
                    roblox_id = info['roblox_id']
            
            if not roblox_id:
                return await interaction.followup.send(
                    " **Verification Required:** You must be verified with Bloxlink to join this session.",
                    ephemeral=True
                )

            group_id = str(blox_cfg.get('group_id', '0'))
            in_group = await interaction.client.is_user_in_group(roblox_id, group_id)
            if not in_group:
                return await interaction.followup.send(
                    f" **Group Lock:** You must be in the Roblox Group ([ID: {group_id}](https://www.roblox.com/groups/{group_id})) to join this session.",
                    ephemeral=True
                )
            return await interaction.followup.send(f"🔗 Session Link: {self.session_link}", ephemeral=True)

        await interaction.response.send_message(f"🔗 Session Link: {self.session_link}", ephemeral=True)


class Reinvites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "pending_sessions"):
            bot.pending_sessions = {}

    @app_commands.command(name="reinvites", description="Request reinvites for the session")
    @app_commands.describe(
        required_reactions="Number of reactions needed",
        session_link="Session link",
        frp_speeds="FRP Speeds",
        peacetime="Peacetime",
        leo="LEO"
    )
    async def reinvites(
        self,
        interaction: discord.Interaction,
        required_reactions: int,
        session_link: str,
        frp_speeds: str,
        peacetime: Literal["Strict", "Normal", "Off"],
        leo: Literal["Active", "Inactive"]
    ):
        staff_role_id = int(self.bot.config['roles']['staff_team'])
        if staff_role_id not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return
        if not session_link.startswith("https://www.roblox.com"):
            await interaction.response.send_message(" Invalid session link. Links must start with `https://www.roblox.com`.", ephemeral=True)
            return
        if not await correct_channel(interaction):
            return
        if not await startup_required(interaction):
            return

        ecfg = _embed_cfg(self.bot, 'reinvites_1')
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Re-Invites___'),
            description=format_embed(ecfg.get('description', ''), self.bot, required=required_reactions),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        civ_role_id = interaction.client.config['roles'].get('civilians')
        ping_content = f"<@&{civ_role_id}>" if civ_role_id else ""

        await interaction.response.send_message("Re-invites initiated.", ephemeral=True)
        message = await interaction.channel.send(
            content=ping_content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        await message.add_reaction("<:tick:1500534096286453782>")

        self.bot.pending_sessions[message.id] = {
            "required": required_reactions,
            "session_link": session_link,
            "frp_speeds": frp_speeds,
            "peacetime": peacetime,
            "leo": leo,
            "user_mention": interaction.user.mention
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in self.bot.pending_sessions:
            return

        target_emoji = "<:tick:1500534096286453782>"
        if str(payload.emoji) != target_emoji:
            return

        data = self.bot.pending_sessions[payload.message_id]
        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        reaction = next((r for r in message.reactions if str(r.emoji) == target_emoji), None)
        if reaction is None:
            return

        users = [u async for u in reaction.users() if not u.bot]
        if len(users) < data["required"]:
            return

        ecfg = _embed_cfg(self.bot, 'reinvites_2')
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Re-Invites___'),
            description=format_embed(ecfg.get('description', ''), self.bot,
                user=data['user_mention'], frp_speeds=data['frp_speeds'],
                peacetime=data['peacetime'], leo=data['leo']),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=self.bot.config['bot']['footer_text'],
            icon_url=self.bot.config['bot']['footer_icon']
        )

        await message.edit(embed=embed, view=SessionButton(data["session_link"]))
        await channel.send("@here Session has been released", allowed_mentions=discord.AllowedMentions(everyone=True))
        del self.bot.pending_sessions[payload.message_id]


async def setup(bot):
    await bot.add_cog(Reinvites(bot))
