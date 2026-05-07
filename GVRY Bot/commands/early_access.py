import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from utils import format_embed
from database import Database

load_dotenv()

def get_allowed_roles(bot):
    roles = bot.config['roles']
    return {
        int(roles.get('civilians', 0)),
        int(roles['staff_team']),
        int(roles.get('Early_access', 0)),
        int(roles.get('server_booster', 0)),
        int(roles['high_command']),
        int(roles['overseer'])
    }

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

def _embed_cfg(client, key):
    return client.config.get('embeds', {}).get(key, {})

class EarlyAccessView(discord.ui.View):
    def __init__(self, session_link: str):
        super().__init__(timeout=None)
        self.session_link = session_link

    @discord.ui.button(label="Session Link", style=discord.ButtonStyle.primary)
    async def session_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
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
        is_deferred = False

        if blox_cfg.get('group_lock_active'):
            await interaction.response.defer(ephemeral=True)
            is_deferred = True
            
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
            
            in_group = await interaction.client.is_user_in_group(roblox_id, blox_cfg.get('group_id'))
            if not in_group:
                return await interaction.followup.send(
                    f" **Group Lock:** You must be in the Roblox Group ([ID: {blox_cfg.get('group_id')}](https://www.roblox.com/groups/{blox_cfg.get('group_id')})) to join this session.",
                    ephemeral=True
                )

        # Roles Check
        user_role_ids = {role.id for role in interaction.user.roles}
        if not user_role_ids.intersection(get_allowed_roles(interaction.client)):
            msg = "You do not have permission to join from the early access button. Please wait for host to release the session or purchase __Early Access__."
            if is_deferred:
                return await interaction.followup.send(msg, ephemeral=True)
            return await interaction.response.send_message(msg, ephemeral=True)
            
        msg = f"🔗 Session Link: {self.session_link}"
        if is_deferred:
            return await interaction.followup.send(msg, ephemeral=True)
        await interaction.response.send_message(msg, ephemeral=True)


class EarlyAccess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="earlyaccess", description="Release early access for session")
    @app_commands.describe(session_link="Session link")
    async def earlyaccess(self, interaction: discord.Interaction, session_link: str):
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

        ecfg = _embed_cfg(interaction.client, 'early_access')
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Early Access___'),
            description=format_embed(ecfg.get('description', ''), interaction.client, user=interaction.user.mention),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )

        view = EarlyAccessView(session_link)
        allowed_roles = get_allowed_roles(self.bot)
        ping_content = " ".join([f"<@&{role_id}>" for role_id in allowed_roles])

        await interaction.response.send_message("Early Access has been released.", ephemeral=True)
        await interaction.channel.send(content=ping_content, embed=embed, view=view, allowed_mentions=discord.AllowedMentions(roles=True))


async def setup(bot):
    await bot.add_cog(EarlyAccess(bot))
