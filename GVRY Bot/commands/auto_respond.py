import discord
from discord.ext import commands

class AutoRespond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1474540648911868005

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself or other bots to prevent loops
        if message.author.bot:
            return

        # Only trigger in the specified channel
        if message.channel.id != self.target_channel_id:
            return

        arrow = "<a:recolored_arrowmove:1499985868541133038>"
        stars = "<a:recolored_recolored_red_stars:1499985951894802553>"

        embed = discord.Embed(
            description=(
                f"> {arrow} **Tired Of The Pings?** Simply Mute this channel! __Right click, Or hold down on this channel and click on ‘mute channel’.__ {stars}\n\n"
                f"> {arrow}  We are currently seeking partners in **__Greenville Roleplay Legacy__**. If you're interested, please feel free to open a **partnership ticket in our ticket channel**<#1474542100145246299>"
            ),
            color=0xadcf8b
        )

        # Use consistent footer from the bot's configuration
        embed.set_footer(
            text=self.bot.config['bot']['footer_text'],
            icon_url=self.bot.config['bot']['footer_icon']
        )

        await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoRespond(bot))
