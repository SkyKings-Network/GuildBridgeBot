import discord
from discord.ext import commands
from core.config import discord as config


class Bridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role(config.commandRole)
    async def invite(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g invite " + username)
        embedVar = discord.Embed(description=username + " has been invited!")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def kick(self, ctx, username, *, reason):
        await self.bot.mineflayer_bot.chat("/g kick " + username + " " + reason)
        embedVar = discord.Embed(description=username + " has been kicked for " + reason + "!")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def promote(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g promote " + username)
        embedVar = discord.Embed(description=username + " has been promoted!")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def mute(self, ctx, username, time):
        await self.bot.mineflayer_bot.chat("/g mute " + username + " " + time)
        embedVar = discord.Embed(description=username + " has been muted for " + time)
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def unmute(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g unmute " + username)
        embedVar = discord.Embed(description=username + " has been unmuted")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def setrank(self, ctx, username, rank):
        await self.bot.mineflayer_bot.chat("/g setrank " + username + " " + rank)
        embedVar = discord.Embed(description=username + " has been promoted to " + rank)
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.commandRole)
    async def demote(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g demote " + username)
        embedVar = discord.Embed(description=username + " has been demoted!")
        await ctx.send(embed=embedVar)

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
