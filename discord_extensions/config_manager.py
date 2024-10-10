import sys
import traceback
from discord.ext import commands
import discord

from core.config import DiscordConfig
from utils.utils import send_temp_message

owner = DiscordConfig.ownerId

def owner_check(ctx):
    return ctx.author.id == owner

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.check(owner_check)
    async def health(self, ctx):
        if self.bot.mineflayer_bot is not None:
                if self.bot.mineflayer_bot.is_online():
                    ctx.send("Online")
                else:
                    ctx.send("Offline")

async def setup(bot):
    await bot.add_cog(Config(bot))