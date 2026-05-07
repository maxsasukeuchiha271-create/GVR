import discord


def get_emoji(bot, emoji_key: str) -> discord.PartialEmoji:
    emoji_config = bot.config['emojis'][emoji_key]
    return discord.PartialEmoji(
        name=emoji_config['name'],
        id=int(emoji_config['id']),
        animated=bool(emoji_config.get('animated', False))
    )

# Commands package for the Discord bot.
# This file allows `commands` to be imported as a Python package.
