import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import time
from typing import Optional, Literal
from database import Database

class MoneyDropView(discord.ui.View):
    def __init__(self, amount: int):
        super().__init__(timeout=None)
        self.amount = amount
        self.claimed = False

    @discord.ui.button(label="Claim Money!", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            return await interaction.response.send_message("This money has already been claimed!", ephemeral=True)
        
        self.claimed = True
        self.stop()
        
        uid = str(interaction.user.id)
        # Ensure user exists and add money
        await Database.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
        await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (self.amount, uid))
            
        embed_color = 0xadcf8b

        embed = discord.Embed(
            title="<:GVRY_pfp:1500241318465638601>  _Greenville Roleplay Yowe_ - ___Money Drop Claimed___",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  {interaction.user.mention} has successfully claimed the **${self.amount:,}** money drop!",
            color=embed_color
        )
        embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

        await interaction.response.send_message(embed=embed)
        try:
            await interaction.message.delete()
        except:
            pass

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.random_drop_task.start()

    def cog_unload(self):
        self.random_drop_task.cancel()

    async def get_user_stats(self, user_id: int):
        uid = str(user_id)
        stats = await Database.fetch_one("SELECT * FROM economy WHERE user_id = ?", (uid,))
        if not stats:
            await Database.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
            stats = await Database.fetch_one("SELECT * FROM economy WHERE user_id = ?", (uid,))
        return stats

    def create_economy_embed(self, interaction: discord.Interaction, title: str, description: str):
        color = 0xadcf8b

        embed = discord.Embed(
            title=f"<a:recolored_recolored_red_stars:1499985951894802553> _Greenville Roleplay Yowe_ - ___ {title} ___ <a:recolored_recolored_red_stars:1499985951894802553>",
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(
            text=interaction.client.config['bot']['footer_text'],
            icon_url=interaction.client.config['bot']['footer_icon']
        )
        return embed

    @app_commands.command(name="balance", description="Check your or another user's balance")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        target = user or interaction.user
        stats = await self.get_user_stats(target.id)
        
        embed = self.create_economy_embed(
            interaction, 
            "Account Balance", 
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Member:__** {target.mention}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Wallet Balance:__** ${stats['wallet']:,}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Bank Balance:__** ${stats['bank']:,}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Total Funds:__** ${(stats['wallet'] + stats['bank']):,}"
        )
        embed.add_field(name="Wallet", value=f"${stats['wallet']:,}", inline=True)
        embed.add_field(name="Bank", value=f"${stats['bank']:,}", inline=True)
        embed.add_field(name="Total", value=f"${(stats['wallet'] + stats['bank']):,}", inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="work", description="Work to earn some money")
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        
        if time.time() - user['last_work'] < 3600:
            remaining = int((3600 - (time.time() - user['last_work'])) / 60)
            return await interaction.followup.send(f"You're tired! You can work again in {remaining} minutes.", ephemeral=True)
            
        earnings = random.randint(500, 1500)
        await Database.execute(
            "UPDATE economy SET wallet = wallet + ?, last_work = ? WHERE user_id = ?", 
            (earnings, time.time(), str(interaction.user.id))
        )
        
        embed = self.create_economy_embed(
            interaction,
            "Work Log",
            f"> <a:recolored_arrowmove:1499985868541133038>  You worked hard and earned **${earnings:,}** for your efforts!"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="crime", description="Commit a crime for a chance at a big payout")
    async def crime(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        
        if time.time() - user['last_crime'] < 1800:
            remaining = int((1800 - (time.time() - user['last_crime'])) / 60)
            return await interaction.followup.send(f"The police are looking for you! Wait {remaining} minutes.", ephemeral=True)
            
        uid = str(interaction.user.id)
        await Database.execute("UPDATE economy SET last_crime = ? WHERE user_id = ?", (time.time(), uid))

        if random.random() < 0.4:
            payout = random.randint(2000, 5000)
            await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (payout, uid))
            embed = self.create_economy_embed(
                interaction,
                "Criminal Records",
                f"> <a:recolored_arrowmove:1499985868541133038>  **__Success!__**\n"
                f"> <a:recolored_arrowmove:1499985868541133038>  Your crime was successful! You managed to steal **${payout:,}**."
            )
        else:
            fine = random.randint(500, 1000)
            await Database.execute("UPDATE economy SET wallet = MAX(0, wallet - ?) WHERE user_id = ?", (fine, uid))
            embed = self.create_economy_embed(
                interaction,
                "Criminal Records",
                f"> <a:recolored_arrowmove:1499985868541133038>  **__Busted!__**\n"
                f"> <a:recolored_arrowmove:1499985868541133038>  You were caught in the act and were fined **${fine:,}** by the authorities."
            )
            embed.color = 0xadcf8b

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="deposit", description="Deposit money into your bank account")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer(ephemeral=True)
        user = await self.get_user_stats(interaction.user.id)
        
        if amount.lower() == "all":
            amt = user['wallet']
        else:
            try:
                amt = int(amount)
            except ValueError:
                return await interaction.followup.send("Please provide a valid number.", ephemeral=True)
        
        if amt <= 0 or amt > user['wallet']:
            return await interaction.followup.send("Invalid amount.", ephemeral=True)
            
        await Database.execute(
            "UPDATE economy SET wallet = wallet - ?, bank = bank + ? WHERE user_id = ?", 
            (amt, amt, str(interaction.user.id))
        )
        
        embed = self.create_economy_embed(
            interaction,
            "Bank Deposit",
            f"> <a:recolored_arrowmove:1499985868541133038>  You have successfully deposited **${amt:,}** into your bank account."
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="withdrawal", description="Withdraw money from your bank account")
    async def withdrawal(self, interaction: discord.Interaction, amount: str):
        await interaction.response.defer(ephemeral=True)
        user = await self.get_user_stats(interaction.user.id)
        
        if amount.lower() == "all":
            amt = user['bank']
        else:
            try:
                amt = int(amount)
            except ValueError:
                return await interaction.followup.send("Please provide a valid number.", ephemeral=True)
        
        if amt <= 0 or amt > user['bank']:
            return await interaction.followup.send("Invalid amount.", ephemeral=True)
            
        await Database.execute(
            "UPDATE economy SET bank = bank - ?, wallet = wallet + ? WHERE user_id = ?", 
            (amt, amt, str(interaction.user.id))
        )
        
        embed = self.create_economy_embed(
            interaction,
            "Bank Withdrawal",
            f"> <a:recolored_arrowmove:1499985868541133038>  You have successfully withdrawn **${amt:,}** from your bank account."
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="collectincome", description="Collect your daily income")
    async def collectincome(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        
        if time.time() - user['last_collect'] < 86400:
            remaining = int((86400 - (time.time() - user['last_collect'])) / 3600)
            return await interaction.followup.send(f"Come back in {remaining} hours for more income.", ephemeral=True)
            
        income = 5000
        await Database.execute(
            "UPDATE economy SET wallet = wallet + ?, last_collect = ? WHERE user_id = ?", 
            (income, time.time(), str(interaction.user.id))
        )
        
        embed = self.create_economy_embed(
            interaction,
            "Income Collection",
            f"> <a:recolored_arrowmove:1499985868541133038>  You have collected your daily income grant of **${income:,}**!"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rob", description="Attempt to rob another user's wallet")
    async def rob(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == interaction.user.id:
            return await interaction.response.send_message("You can't rob yourself!", ephemeral=True)
            
        await interaction.response.defer()
        robber = await self.get_user_stats(interaction.user.id)
        victim = await self.get_user_stats(user.id)
        
        if victim['wallet'] < 500:
            return await interaction.followup.send("This person is too poor to rob.", ephemeral=True)
            
        robber_id = str(interaction.user.id)
        victim_id = str(user.id)

        if random.random() < 0.3:
            stolen = random.randint(100, victim['wallet'] // 2)
            await Database.execute("UPDATE economy SET wallet = wallet - ? WHERE user_id = ?", (stolen, victim_id))
            await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (stolen, robber_id))

            embed = self.create_economy_embed(
                interaction,
                "Robbery Incident",
                f"> <a:recolored_arrowmove:1499985868541133038>  You successfully robbed {user.mention} and got away with **${stolen:,}**!"
            )
        else:
            fine = 1000
            await Database.execute("UPDATE economy SET wallet = MAX(0, wallet - ?) WHERE user_id = ?", (fine, robber_id))
            embed = self.create_economy_embed(
                interaction,
                "Robbery Incident",
                f"> <a:recolored_arrowmove:1499985868541133038>  Your attempt to rob {user.mention} failed. You were caught and fined **${fine:,}**."
            )
            embed.color = 0xadcf8b
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="economy_leaderboard", description="Show the richest players")
    async def economy_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        top_users = await Database.fetch_all(
            "SELECT user_id, wallet, bank, (wallet + bank) as total FROM economy ORDER BY total DESC LIMIT 10"
        )
        
        embed = self.create_economy_embed(
            interaction,
            "Economy Leaderboard",
            ""
        )
        desc = ""
        for i, row in enumerate(top_users, 1):
            member = interaction.guild.get_member(int(row['user_id']))
            name = member.display_name if member else f"User {row['user_id']}"
            total = row['total']
            desc += f"**{i}.** {name} - ${total:,}\n"
            
        embed.description = desc
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="givemoney", description="Give money to a user (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def givemoney(self, interaction: discord.Interaction, user: discord.Member, count: int):
        await interaction.response.defer(ephemeral=True)
        uid = str(user.id)
        await Database.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (uid,))
        await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (count, uid))
        
        embed = self.create_economy_embed(
            interaction,
            "Administrative Grant",
            f"> <a:recolored_arrowmove:1499985868541133038>  **${count:,}** has been successfully added to {user.mention}'s wallet by an administrator."
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="moneydrop", description="Start a money drop in the channel (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def moneydrop(self, interaction: discord.Interaction, amount: int):
        view = MoneyDropView(amount)
        embed = discord.Embed(
            title=" _Greenville Roleplay Yowe_ - ___Money Drop___",
            description=f"> <a:recolored_arrowmove:1499985868541133038>  A surprise drop of **${amount:,}** has appeared!\n"
                        f"> <a:recolored_arrowmove:1499985868541133038>  Be the first to click the button below to claim it!",
            color=0xadcf8b
        )

        embed.set_footer(text=interaction.client.config['bot']['footer_text'], icon_url=interaction.client.config['bot']['footer_icon'])

        await interaction.response.send_message("Money drop initiated.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="blackjack", description="Play blackjack against the dealer")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        if bet <= 0 or bet > user['wallet']: return await interaction.followup.send("Invalid bet.", ephemeral=True)
        
        uid = str(interaction.user.id)
        user_score, dealer_score = random.randint(15, 21), random.randint(15, 22)
        if dealer_score > 21 or user_score > dealer_score:
            await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (bet, uid))
            result = f"**Winner!** You beat the dealer's score of {dealer_score} with your {user_score}."
        elif user_score == dealer_score: 
            result = f"**Push (Tie)!** Both you and the dealer had {user_score}. Your bet was returned."
        else:
            await Database.execute("UPDATE economy SET wallet = wallet - ? WHERE user_id = ?", (bet, uid))
            result = f"**Bust!** The dealer won with a score of {dealer_score}. Your {user_score} wasn't enough."
        
        embed = self.create_economy_embed(
            interaction,
            "Blackjack Table",
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Bet Amount:__** ${bet:,}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Result:__** {result}"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roulette", description="Bet on a color in roulette")
    async def roulette(self, interaction: discord.Interaction, bet: int, color: Literal["red", "black", "green"]):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        if bet <= 0 or bet > user['wallet']: return await interaction.followup.send("Invalid bet.", ephemeral=True)
        
        uid = str(interaction.user.id)
        res = random.choice(["red"] * 18 + ["black"] * 18 + ["green"] * 2)
        if res == color:
            mult = 14 if color == "green" else 2
            await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (bet * mult - bet, uid))
            msg = f"The wheel landed on **{res.capitalize()}**! You won **${bet*mult:,}**!"
        else:
            await Database.execute("UPDATE economy SET wallet = wallet - ? WHERE user_id = ?", (bet, uid))
            msg = f"The wheel landed on **{res.capitalize()}**. Better luck next time!"
        
        embed = self.create_economy_embed(
            interaction,
            "Roulette Wheel",
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Bet Color:__** {color.capitalize()}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Outcome:__** {msg}"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cockfight", description="Bet on a cockfight")
    async def cockfight(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        user = await self.get_user_stats(interaction.user.id)
        if bet <= 0 or bet > user['wallet']: return await interaction.followup.send("Invalid bet.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if random.random() < 0.5:
            await Database.execute("UPDATE economy SET wallet = wallet + ? WHERE user_id = ?", (bet, uid))
            msg = "Your prize bird triumphed in the arena! You've doubled your bet."
        else:
            await Database.execute("UPDATE economy SET wallet = wallet - ? WHERE user_id = ?", (bet, uid))
            msg = "Your bird was defeated. Better luck next time in the arena."
        
        embed = self.create_economy_embed(
            interaction,
            "Cockfight Arena",
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Bet Amount:__** ${bet:,}\n"
            f"> <a:recolored_arrowmove:1499985868541133038>  **__Result:__** {msg}"
        )
        await interaction.followup.send(embed=embed)

    @tasks.loop(minutes=15)
    async def random_drop_task(self):
        """Periodically triggers a random money drop in the session channel."""
        # ~4% chance to trigger every 15 minutes (roughly once every 6 hours on average)
        if random.random() < 0.04:
            amount = random.randint(1000, 5000)
            
            try:
                # Attempt to get the session channel ID from the bot's config
                channel_id = int(self.bot.config['channels']['money_drop_channel_id'])
                channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
                
                if channel:
                    view = MoneyDropView(amount)
                    embed = discord.Embed(
                        title="_Greenville Roleplay Yowe_ - ___Money Drop___",
                        description=f"> <a:recolored_arrowmove:1499985868541133038>  A surprise drop of **${amount:,}** has appeared!\n"
                                    f"> <a:recolored_arrowmove:1499985868541133038>  Be the first to click the button below to claim it!",
                        color=0xadcf8b
                    )
                    embed.set_footer(text=self.bot.config['bot']['footer_text'], icon_url=self.bot.config['bot']['footer_icon'])
                    await channel.send(embed=embed, view=view)
            except Exception:
                # Silently fail if channel is inaccessible or config is missing
                pass

async def setup(bot):
    await bot.add_cog(Economy(bot))