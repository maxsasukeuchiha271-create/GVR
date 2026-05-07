"""Shared utilities for the GVRY bot."""

class _SafeDict(dict):
    """dict that returns {key} for missing keys so unknown placeholders stay visible."""
    def __missing__(self, key):
        return '{' + key + '}'

def format_embed(text: str, client, **kwargs) -> str:
    """
    Substitute emoji_vars from config first, then runtime placeholders.
    Unknown placeholders are left as-is so a typo doesn't crash the bot.
    """
    if not text:
        return text
    emoji_vars = client.config.get('emoji_vars', {})
    all_vars = _SafeDict({**emoji_vars, **kwargs})
    try:
        return text.format_map(all_vars)
    except Exception:
        return text
