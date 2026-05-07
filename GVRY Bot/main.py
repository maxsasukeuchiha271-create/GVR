import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import aiohttp
from discord import app_commands
import traceback
import json
from pathlib import Path
from database import Database
import logging
from collections import deque

# Buffer for live logs (shared with dashboard)
log_buffer = deque(maxlen=100)
class BufferHandler(logging.Handler):
    def emit(self, record):
        log_buffer.append(self.format(record))

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
BASE_DIR = Path(__file__).resolve().parent

def load_config():
    config_path = BASE_DIR / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.addHandler(BufferHandler())

def get_prefix(bot, message):
    return bot.config['bot'].get('prefix', '.')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.config = config  # Store config in bot instance
bot.base_dir = BASE_DIR
bot.pending_sessions = {}
bot.session_states = {}
bot.log_buffer = log_buffer

def format_embed(config, key, **kwargs):
    """Helper to create an embed from config with placeholder replacement."""
    data = config.get('embeds', {}).get(key, {})
    title = data.get('title', 'Embed Title')
    description = data.get('description', 'Embed Description')
    image_url = data.get('image_url', '')

    # Replace Emoji Variables
    for name, val in config.get('emoji_vars', {}).items():
        title = title.replace(f"{{{name}}}", val)
        description = description.replace(f"{{{name}}}", val)

    # Replace Runtime Placeholders
    for k, v in kwargs.items():
        title = title.replace(f"{{{k}}}", str(v))
        description = description.replace(f"{{{k}}}", str(v))

    embed = discord.Embed(
        title=title,
        description=description,
        color=int(config['bot']['embed_color'].replace('#', ''), 16)
    )
    if image_url: embed.set_image(url=image_url)
    embed.set_footer(text=config['bot']['footer_text'], icon_url=config['bot']['footer_icon'])
    return embed

async def fetch_roblox_info(self, user_id: int, guild_id: str = None):
    """Fetches Roblox ID and Username using Bloxlink API v4 with global fallback."""
    blox_cfg = self.config.get('bloxlinks', {})
    api_key = blox_cfg.get('api_key', '').strip()
    
    # Determine the target guild: prioritize passed ID, then env variable
    target_guild = guild_id or GUILD_ID
    
    if not api_key:
        logger.warning("Bloxlink API key missing in config.json. Cannot fetch Roblox info.")
        return None

    headers = {
        "Authorization": api_key,
        "User-Agent": "GVRY-Bot/1.0 (Discord Bot)"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            data = None
            
            # 1. Try Guild-Specific Check first (Most reliable for server API keys)
            if target_guild and target_guild != "None":
                url = f"https://api.blox.link/v4/public/guild/{target_guild}/discord-user/{user_id}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                    elif resp.status not in [404, 401, 403]:
                        logger.debug(f"Bloxlink Guild API returned {resp.status} for {user_id}")

            # 2. Fallback to Global Check if guild check failed or wasn't possible
            if not data or (not data.get("robloxID") and not data.get("robloxId")):
                url = f"https://api.blox.link/v4/public/discord-user/{user_id}"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                    elif resp.status == 401:
                        logger.error(f"Bloxlink API Key is INVALID. Status 401 for user {user_id}.")
                    elif resp.status == 403:
                        logger.warning(f"Bloxlink API Key lacks 'Global' permissions. Status 403 for user {user_id}.")
                    elif resp.status != 404:
                        resp_text = await resp.text()
                        logger.warning(f"Bloxlink Global API error {resp.status} for {user_id}: {resp_text}")

            # Support both robloxID (standard) and robloxId (fallback)
            rid = data.get("robloxID") or data.get("robloxId") if data else None

            if rid:
                return {
                    "roblox_id": str(rid),
                    "username": data.get("resolved", {}).get("roblox", {}).get("name", "Unknown")
                }
            else:
                if data and "error" in data:
                    logger.info(f"Bloxlink API returned error for {user_id}: {data['error']}")

    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to Bloxlink API for user {user_id}: {e}")
    return None # Return None if API call fails or status is not 200

async def is_user_in_group(roblox_id: str, group_id: str):
    """Checks if a Roblox ID is in a specific group via Roblox API."""
    if not roblox_id or not group_id or group_id == "0":
        logger.debug(f"Skipping group check: roblox_id={roblox_id}, group_id={group_id}. Assuming user is in group.")
        return True
        
    # Ensure group_id is treated as a string for comparison
    group_id_str = str(group_id)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    url = f"https://groups.roblox.com/v1/users/{roblox_id}/groups/roles"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    groups = data.get("data", [])
                    return any(str(g.get("group", {}).get("id")) == group_id_str for g in groups)
                else:
                    logger.warning(f"Roblox Group API returned status {resp.status} for user {roblox_id}. Response: {await resp.text()}")
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to Roblox Group API for user {roblox_id}: {e}")
    return False # Return False if API call fails or status is not 200

async def verify_user(self, member: discord.Member):
    """
    Auto-links Roblox profile (DB) for ANY verified user.
    Assigns Civilian role ONLY if they are in the group.
    """
    uid = str(member.id)
    
    # Pass the member's guild ID to fetch_roblox_info for better accuracy
    info = await self.fetch_roblox_info(member.id, guild_id=str(member.guild.id))
    
    # Check DB if API fails
    if not info or not info.get('roblox_id'):
        existing = await Database.fetch_one("SELECT roblox_id, roblox_username FROM economy WHERE user_id = ?", (uid,))
        if existing and existing.get('roblox_id'):
            info = {'roblox_id': existing['roblox_id'], 'username': existing['roblox_username']}
        else:
            logger.info(f"Verification lookup failed for {member.display_name}. Not verified on Bloxlink?")
            return None

    existing = await Database.fetch_one("SELECT roblox_id FROM economy WHERE user_id = ?", (uid,))
    # 1. Link profile in Database (Update if missing or changed)
    if not existing or existing.get('roblox_id') != info['roblox_id']:
        await Database.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
        await Database.execute(
            "UPDATE economy SET roblox_id = ?, roblox_username = ? WHERE user_id = ?",
            (info['roblox_id'], info['username'], uid)
        )

    # 2. Check Group & Assign Civilian Role
    blox_cfg = self.config.get('bloxlinks', {})
    civ_role_id = self.config['roles'].get('civilians')
    
    if civ_role_id:
        role = member.guild.get_role(int(civ_role_id))
        if role:
            is_in_group = await self.is_user_in_group(info['roblox_id'], blox_cfg.get('group_id'))
            if is_in_group:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Verified via Roblox Group.")
                    except discord.Forbidden:
                        logger.error(f"Failed to add role to {member.name}: Check bot role hierarchy.")

    return info

bot.fetch_roblox_info = fetch_roblox_info
bot.fetch_roblox_info = fetch_roblox_info.__get__(bot, commands.Bot)
bot.is_user_in_group = is_user_in_group
bot.verify_user = verify_user.__get__(bot, commands.Bot)

@bot.tree.command(name="verify", description="Manually link your Roblox account and update your roles")
async def verify_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    info = await bot.verify_user(interaction.user)
    
    if not info:
        return await interaction.followup.send(
            "❌ **Verification Failed:** I couldn't find a Roblox account linked to your Discord via Bloxlink.\n"
            "Please verify at [blox.link](https://blox.link/) first.",
            ephemeral=True
        )

    blox_cfg = bot.config.get('bloxlinks', {})
    is_in_group = await bot.is_user_in_group(info['roblox_id'], blox_cfg.get('group_id'))
    
    status_msg = f"✅ **Success!** Your profile is linked to `{info['username']}`."
    if is_in_group:
        status_msg += "\n🎖️ You are in the Roblox Group and have been granted the Civilian role."
    else:
        group_id = blox_cfg.get('group_id')
        status_msg += f"\n⚠️ You are **not** in the Roblox Group (ID: {group_id}). You won't be able to join sessions."

    await interaction.followup.send(status_msg, ephemeral=True)

def command_permission_check(command_path: str):
    """
    A custom application command check decorator that verifies if the interacting user
    has the necessary roles defined in the bot's configuration for a given command.
    
    Special keywords:
    - "admin": Requires the user to have administrator guild permissions.
    - "staff_team": Requires the user to have the role ID specified in config['roles']['staff_team'].
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        required_roles_config = interaction.client.config.get('permissions', {}).get(command_path)

        if required_roles_config is None:
            return True # No specific roles defined, allow by default

        if "admin" in required_roles_config and interaction.user.guild_permissions.administrator:
            return True

        staff_role_id_str = interaction.client.config['roles'].get('staff_team')
        if "staff_team" in required_roles_config and staff_role_id_str:
            try:
                staff_role_id = int(staff_role_id_str)
                if staff_role_id in [role.id for role in interaction.user.roles]:
                    return True
            except ValueError:
                pass

        if any(str(role.id) in required_roles_config for role in interaction.user.roles):
            return True

        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

bot.format_embed = format_embed

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    log_channel_id = int(bot.config['channels']['mod_logs_channel_id'])
    channel = bot.get_channel(log_channel_id)
    if channel:
        embed = bot.format_embed(bot.config, 'message_delete',
            user=message.author.mention,
            user_id=message.author.id,
            channel=message.channel.mention,
            content=message.content or '*(No text content)*'
        )
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_member_join(member):
    """Auto-links Roblox profile and sends a welcome message."""
    # 1. Run the auto-verification/linking logic
    await bot.verify_user(member)
    
    # 2. Welcome message (Handled here to ensure it only happens once)
    # Fallback to the known welcome channel ID if not in config
    welcome_channel_id = bot.config['channels'].get('welcome_channel_id') or 1474542358094676030
    if welcome_channel_id:
        channel = bot.get_channel(int(welcome_channel_id))
        if channel:
            embed = bot.format_embed(bot.config, 'welcome', user=member.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    log_channel_id = int(bot.config['channels']['mod_logs_channel_id'])
    channel = bot.get_channel(log_channel_id)
    if channel:
        embed = bot.format_embed(bot.config, 'message_edit',
            user=before.author.mention,
            user_id=before.author.id,
            channel=before.channel.mention,
            jump_url=after.jump_url,
            before=before.content[:1024] or "*(No content)*",
            after=after.content[:1024] or "*(No content)*"
        )
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        # Use dedicated command logs channel, fallback to mod logs if not set
        log_channel_id_str = bot.config['channels'].get('command_logs_channel_id') or bot.config['channels'].get('mod_logs_channel_id')
        if not log_channel_id_str or log_channel_id_str == "0":
            return
            
        log_channel_id = int(log_channel_id_str)
        channel = bot.get_channel(log_channel_id)
        if channel:
            command_name = interaction.command.name if interaction.command else "Unknown"
            user = interaction.user
            embed = bot.format_embed(bot.config, 'command_used',
                user=user.mention,
                user_id=user.id,
                command=command_name,
                channel=interaction.channel.mention
            )
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)

@bot.event
async def on_ready():
    if hasattr(bot, "_synced"):
        return

    # Load Persistent Views (Imports from specific Cog files)
    try:
        from commands.tickets import TicketPanelView, TicketActionsView
    except ImportError:
        from tickets import TicketPanelView, TicketActionsView
        
    # TicketPanelView is not persistent as its options are dynamic based on config
    bot.add_view(TicketActionsView())
    
    # We pass None for host as it's a generic persistent view for the button
    try:
        from commands.over import FeedbackView
    except ImportError:
        from over import FeedbackView
        
    bot.add_view(FeedbackView(None))

    print(f'Logged in as {bot.user}')
    
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
    else:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands globally.')

    bot._synced = True

# Load commands from commands folder
async def load_commands():
    commands_path = BASE_DIR / 'commands'
    prefix = "commands."
    
    if not commands_path.exists():
        # Fallback to root directory if 'commands' folder is missing
        print(f"Note: 'commands' directory not found. Loading from root: {BASE_DIR}")
        commands_path = BASE_DIR
        prefix = ""

    # Files in the root that should never be loaded as Cogs
    ignored_files = {"main.py", "database.py"}

    for file in commands_path.glob("*.py"):
        if file.name != "__init__.py" and file.name not in ignored_files:
            extension = f'{prefix}{file.stem}'
            print(f'Loading extension: {extension}')
            try:
                await bot.load_extension(extension)
            except Exception:
                print(f' Failed to load extension {extension}:')
                traceback.print_exc()

async def main():
    from dashboard_api import start_dashboard_api
    async with bot:
        await Database.initialize()
        await load_commands()
        await start_dashboard_api(bot)
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())