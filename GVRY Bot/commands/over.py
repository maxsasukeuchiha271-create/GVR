import discord
from discord import app_commands
from discord.ext import commands
import time
from utils import format_embed

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

class FeedbackModal(discord.ui.Modal, title='Session Feedback'):
    additional_notes = discord.ui.TextInput(
        label='Additional Notes',
        style=discord.TextStyle.paragraph,
        placeholder='Enter any additional notes here...',
        required=False,
        max_length=1000,
    )

    def __init__(self, host: discord.User, rating: str):
        super().__init__()
        self.host = host
        self.rating = rating

    async def on_submit(self, interaction: discord.Interaction):
        try:
            feedback_channel_id = int(interaction.client.config['channels']['feedback_Channel_id'])
            channel = interaction.client.get_channel(feedback_channel_id) or interaction.guild.get_channel(feedback_channel_id)
            if not channel:
                channel = await interaction.client.fetch_channel(feedback_channel_id)
            if channel:
                embed = discord.Embed(title="Session Feedback", color=0xadcf8b)
                embed.add_field(name="Host", value=self.host.mention, inline=True)
                embed.add_field(name="User", value=interaction.user.mention, inline=True)
                embed.add_field(name="Rating", value=self.rating, inline=True)
                embed.add_field(name="Additional Notes", value=self.additional_notes.value or "None", inline=False)
                embed.set_footer(text=f"Feedback from {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
                await channel.send(embed=embed)
                await interaction.response.send_message("Thank you for your feedback!", ephemeral=True)
            else:
                await interaction.response.send_message(" Feedback channel not found. Please contact staff.", ephemeral=True)
        except Exception as e:
            print(f"Feedback Error: {e}")
            await interaction.response.send_message(" An error occurred while sending feedback.", ephemeral=True)

class FeedbackView(discord.ui.View):
    def __init__(self, host: discord.User):
        super().__init__(timeout=None)
        self.host = host

    @discord.ui.button(label="Session Feedback", style=discord.ButtonStyle.secondary, emoji="📝", custom_id="session_feedback_button")
    async def feedback_button(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_message(
            "Please select a rating for the session:",
            view=RatingView(self.host),
            ephemeral=True
        )

class RatingView(discord.ui.View):
    def __init__(self, host: discord.User):
        super().__init__(timeout=300)
        self.host = host

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, custom_id="rating_1")
    async def rating_1(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.host, "1"))

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, custom_id="rating_2")
    async def rating_2(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.host, "2"))

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, custom_id="rating_3")
    async def rating_3(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.host, "3"))

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, custom_id="rating_4")
    async def rating_4(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.host, "4"))

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, custom_id="rating_5")
    async def rating_5(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(FeedbackModal(self.host, "5"))

class Over(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="over", description="End the roleplay session")
    @app_commands.describe(notes="Notes for the session end")
    async def over(self, ctx: discord.Interaction, notes: str):
        if int(ctx.client.config['roles']['staff_team']) not in [role.id for role in ctx.user.roles]:
            await ctx.response.send_message(" Only staff team members can use this command.", ephemeral=True)
            return
        if not await correct_channel(ctx):
            return
        if not await startup_required(ctx):
            return

        states = getattr(self.bot, 'session_states', {})
        start_time_val = states.get(ctx.channel_id, {}).get('time') or int(time.time())
        start_time = f"<t:{start_time_val}:t>"
        end_time = f"<t:{int(time.time())}:t>"

        ecfg = ctx.client.config.get('embeds', {}).get('over', {})
        embed = discord.Embed(
            title=ecfg.get('title', '_Greenville Roleplay Yowe_ - ___Roleplay Conclusion:___'),
            description=format_embed(ecfg.get('description', ''), ctx.client,
                user=ctx.user.mention, start_time=start_time,
                end_time=end_time, notes=notes),
            color=0xadcf8b
        )
        image_url = ecfg.get('image_url', '')
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=ctx.client.config['bot']['footer_text'],
            icon_url=ctx.client.config['bot']['footer_icon']
        )

        if hasattr(self.bot, 'session_states') and ctx.channel_id in self.bot.session_states:
            del self.bot.session_states[ctx.channel_id]

        await ctx.response.send_message("Session has been concluded.", ephemeral=True)
        sent_message = await ctx.channel.send(embed=embed, view=FeedbackView(ctx.user))

        def is_not_pinned(m):
            return not m.pinned and m.id != sent_message.id

        await ctx.channel.purge(limit=None, check=is_not_pinned)

async def setup(bot):
    await bot.add_cog(Over(bot))
