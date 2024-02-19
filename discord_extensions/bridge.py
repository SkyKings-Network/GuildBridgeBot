import discord
from discord.ext import commands
from core.config import discord as config


class Bridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role(config.commandRole)
    async def invite(self, ctx, username):
        result = await self.bot.send_invite(username)
        if not result[0] and result[1] == "timeout":
            embedVar = discord.Embed(description="Something went wrong trying to send an invite. Try again later.", color=discord.Color.red())
            await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def kick(self, ctx, username, *, reason):
        await self.bot.mineflayer_bot.chat("/g kick " + username + " " + reason)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def promote(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g promote " + username)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def mute(self, ctx, username, time):
        await self.bot.mineflayer_bot.chat("/g mute " + username + " " + time)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def unmute(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g unmute " + username)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def setrank(self, ctx, username, rank):
        await self.bot.mineflayer_bot.chat("/g setrank " + username + " " + rank)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def demote(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g demote " + username)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def online(self, ctx):
        await self.bot.mineflayer_bot.chat("/g online")

    @commands.command(name="list")
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def _list(self, ctx):
        await self.bot.mineflayer_bot.chat("/g list")


async def setup(bot):
    await bot.add_cog(Bridge(bot))
