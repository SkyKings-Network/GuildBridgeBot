import asyncio

import discord
from discord.ext import commands
from core.config import DiscordConfig


class Bridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def invite(self, ctx, username):
        result = await self.bot.send_invite(username)
        await self.bot.send_debug_message(f"Invite to {username}: {result}")
        if not result[0] and result[1] == "timeout":
            embed = discord.Embed(
                description="Something went wrong trying to send an invite. Try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def kick(self, ctx, username, *, reason):
        await self.bot.mineflayer_bot.chat("/g kick " + username + " " + reason)

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def promote(self, ctx, username):
        await self.bot.mineflayer_bot.chat("/g promote " + username)

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def mute(self, ctx, username, time):
        message = await ctx.send(
            embed=discord.Embed(
                description="Sending mute command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g mute " + username + " " + time)
        try:
            res = await self.bot.wait_for(
                "hypixel_guild_member_muted",
                check=lambda p, m, d: m.lower() == username.lower(),
                timeout=5
            )
        except asyncio.TimeoutError:
            await message.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was muted.",
                    color=discord.Color.red()
                )
            )
        else:
            await message.edit(
                embed=discord.Embed(
                    description=f"Muted {username} for {res[2]}.",
                    color=discord.Color.green()
                )
            )

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def unmute(self, ctx, username):
        message = await ctx.send(
            embed=discord.Embed(
                description="Sending unmute command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g unmute " + username)
        try:
            await self.bot.wait_for(
                "hypixel_guild_member_unmuted",
                check=lambda p, m: m.lower() == username.lower(),
                timeout=5
            )
        except asyncio.TimeoutError:
            await message.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was unmuted.",
                    color=discord.Color.red()
                )
            )
        else:
            await message.edit(
                embed=discord.Embed(
                    description=f"Unmuted {username}.",
                    color=discord.Color.green()
                )
            )

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def setrank(self, ctx, username, rank):
        await self.bot.mineflayer_bot.chat("/g setrank " + username + " " + rank)

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
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

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def top(self, ctx, date_int = 0):
        await self.bot.mineflayer_bot.chat(f"/g top {date_int}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def info(self, ctx):
        await self.bot.mineflayer_bot.chat("/g info")

async def setup(bot):
    await bot.add_cog(Bridge(bot))
