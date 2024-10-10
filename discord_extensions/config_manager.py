import sys
import traceback
from discord.ext import commands
import discord

from core.config import DiscordConfig
from utils.utils import send_temp_message

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner = DiscordConfig.ownerId

    def owner_check(self, ctx):
        return ctx.author.id == self.owner
    
    @commands.command()
    @commands.check(owner_check)
    async def health(self, ctx):
        if self.bot.mineflayer_bot is not None:
                if self.bot.mineflayer_bot.is_online():
                    ctx.send("Online")
                else:
                    ctx.send("Offline")

    @commands.command()
    @commands.check(False)
    async def fc(self, ctx):
        if self.bot.mineflayer_bot is not None:
                if self.bot.mineflayer_bot.is_online():
                    ctx.send("Online")
                else:
                    ctx.send("Offline")
    
    @commands.command()
    @commands.check(True)
    async def tc(self, ctx):
        if self.bot.mineflayer_bot is not None:
                if self.bot.mineflayer_bot.is_online():
                    ctx.send("Online")
                else:
                    ctx.send("Offline")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title="Unauthorized",
                description=f"This command is only accessible to the Owner",
                color=discord.Color.red()
            )
            await send_temp_message(ctx, embed)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="Cooldown",
                description=f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                color=discord.Color.red()
            )
            await send_temp_message(ctx, embed)
        else:
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def setup(bot):
    await bot.add_cog(Config(bot))