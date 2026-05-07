import discord
from discord import app_commands
from discord.ext import commands
import time
from utils import format_embed

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

class Startup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'session_states'):
            bot.session_states = {}

    @app_commands.command(name="startup", description="Start a roleplay session")
    @app_commands.describe(required_reactions="Number of reactions needed to start the session")
    async def startup(self, ctx: discord.Interaction, required_reactions: int):
        staff_role_id = int(ctx.client.config['roles']['staff_team'])
        if staff_role_id not in [role.id for role in ctx.user.roles]:
            await ctx.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return
        if not await correct_channel(ctx):
            return

        ecfg = _embed_cfg(ctx.client, 'startup')
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Session Startup___'),
            description=format_embed(ecfg.get('description', ''), ctx.client, user=ctx.user.mention, required=required_reactions),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=ctx.client.config['bot']['footer_text'],
            icon_url=ctx.client.config['bot']['footer_icon']
        )

        await ctx.response.send_message(" Startup initiated.", ephemeral=True)
        message = await ctx.channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))
        await message.add_reaction("<:tick:1500534096286453782>")

        self.bot.session_states[ctx.channel_id] = {
            'message_id': message.id,
            'time': int(time.time()),
            'completed': True,
            'reactors': set()
        }
        self.bot.pending_sessions[message.id] = {
            'type': 'startup',
            'required': required_reactions,
            'user': ctx.user.mention
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        emoji_str = str(payload.emoji)
        target_emoji = "<:tick:1500534096286453782>"

        if hasattr(self.bot, 'session_states'):
            for state in self.bot.session_states.values():
                if payload.message_id == state['message_id'] and emoji_str == target_emoji:
                    state['reactors'].add(payload.user_id)
                    break

        if payload.message_id not in self.bot.pending_sessions:
            return

        data = self.bot.pending_sessions[payload.message_id]
        if data.get('type') != 'startup' or emoji_str != target_emoji:
            return

        channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        reaction = next((r for r in message.reactions if str(r) == target_emoji), None)
        if reaction is None:
            return

        users = [u async for u in reaction.users() if not u.bot]
        if len(users) < data['required']:
            return

        ecfg = _embed_cfg(self.bot, 'setup')
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Roleplay Preparation:___'),
            description=format_embed(ecfg.get('description', ''), self.bot, user=data['user']),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=self.bot.config['bot']['footer_text'],
            icon_url=self.bot.config['bot']['footer_icon']
        )
        await channel.send(embed=embed)
        del self.bot.pending_sessions[payload.message_id]

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        target_emoji = "<:tick:1500534096286453782>"
        if hasattr(self.bot, 'session_states'):
            for state in self.bot.session_states.values():
                if payload.message_id == state['message_id'] and str(payload.emoji) == target_emoji:
                    state['reactors'].discard(payload.user_id)
                    break

async def setup(bot):
    await bot.add_cog(Startup(bot))
