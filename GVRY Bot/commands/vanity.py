import discord
from discord.ext import commands

class Vanity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self):
        return self.bot.config.get('vanity', {
            'code': '/GVRY',
            'role_id': '1452886857267417245',
            'log_channel_id': '1452886966604398727',
            'embed_title': 'Greenville Roleplay Legacy - Appreciation!',
            'embed_description': '> We thank {user} for applying the `{code}` vanity code! You have been rewarded with the {role} role!',
            'remove_role_on_remove': True
        })

    @commands.Cog.listener()
    async def on_presence_update(self, _before: discord.Member, after: discord.Member):
        if after.bot:
            return

        cfg = self._cfg()
        vanity_code = cfg.get('code', '/GVRY')
        vanity_role_id = int(cfg.get('role_id', 0))
        log_channel_id = int(cfg.get('log_channel_id', 0))

        has_vanity = any(
            isinstance(a, discord.CustomActivity) and a.name and vanity_code.lower() in a.name.lower()
            for a in after.activities
        )

        role = after.guild.get_role(vanity_role_id)
        if not role:
            return

        if has_vanity:
            if role not in after.roles:
                try:
                    await after.add_roles(role, reason="Vanity status code detected.")

                    channel = self.bot.get_channel(log_channel_id)
                    if not channel:
                        try:
                            channel = await self.bot.fetch_channel(log_channel_id)
                        except discord.NotFound:
                            return

                    if channel:
                        desc = cfg.get(
                            'embed_description',
                            '> We thank {user} for applying the `{code}` vanity code! You have been rewarded with the {role} role!'
                        ).format(user=after.mention, code=vanity_code, role=role.mention)

                        embed = discord.Embed(
                            title=cfg.get('embed_title', 'Greenville Roleplay Yowe - Appreciation!'),
                            description=desc,
                            color=0xadcf8b
                        )
                        embed.set_footer(
                            text=self.bot.config['bot']['footer_text'],
                            icon_url=self.bot.config['bot']['footer_icon']
                        )
                        await channel.send(embed=embed)
                except discord.Forbidden:
                    print(f"Permissions error: Could not add vanity role to {after.display_name}")
                except Exception as e:
                    print(f"Error in vanity role assignment: {e}")
        else:
            if role in after.roles and cfg.get('remove_role_on_remove', True):
                try:
                    await after.remove_roles(role, reason="Vanity status code removed.")
                except discord.Forbidden:
                    pass
                except Exception as e:
                    print(f"Error removing vanity role: {e}")

async def setup(bot):
    await bot.add_cog(Vanity(bot))
