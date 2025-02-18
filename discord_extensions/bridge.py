import asyncio
import sys
import traceback

import discord
from discord.ext import commands
from core.config import DiscordConfig, SettingsConfig


class Bridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.date_limit = SettingsConfig.dateLimit
        if self.date_limit < 0:
            self.date_limit = 30

    @commands.command(aliases=['i'])
    @commands.has_role(DiscordConfig.commandRole)
    async def invite(self, ctx, username):
        msg = await ctx.reply(
            embed=discord.Embed(
                description="Sending invite command...",
                color=discord.Color.gold()
            )
        )
        result = await self.bot.send_invite(username)
        await self.bot.send_debug_message(f"Invite to {username}: {result}")
        if not result[0] and result[1] == "timeout":
            embed = discord.Embed(
                description="Something went wrong trying to send an invite.",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
        elif not result[0]:
            embed = discord.Embed(
                description=f"Could not invite {username} to the guild.",
                color=discord.Color.red()
            )
            await msg.edit(embed=embed)
        else:
            embed = discord.Embed(
                description=f"Invited {username} to the guild!",
                color=discord.Color.green()
            )
            await msg.edit(embed=embed)

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def kick(self, ctx, username, *, reason):
        message = await ctx.send(
            embed=discord.Embed(
                description="Sending kick command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g kick " + username + " " + reason)
        try:
            username = await self.bot.wait_for(
                "hypixel_guild_member_kick",
                check=lambda m: m.lower() == username.lower(),
                timeout=5
            )
        except asyncio.TimeoutError:
            await message.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was kicked.",
                    color=discord.Color.red()
                )
            )
        else:
            await message.edit(
                embed=discord.Embed(
                    description=f"Kicked {username} from the guild.",
                    color=discord.Color.green()
                )
            )

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
        msg = await ctx.reply(
            embed=discord.Embed(
                description="Sending setrank command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g setrank " + username + " " + rank)
        try:
            username, from_rank, to_rank = await asyncio.wait(
                [
                    self.bot.wait_for(
                        "hypixel_guild_member_demote",
                        check=lambda p, f, t: p.lower() == username.lower() and t.lower() == rank.lower()
                    ),
                    self.bot.wait_for(
                        "hypixel_guild_member_promote",
                        check=lambda p, f, t: p.lower() == username.lower() and t.lower() == rank.lower()
                    )
                ],
                timeout=10,
                return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.TimeoutError:
            await msg.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was set to {rank}.",
                    color=discord.Color.red()
                )
            )
        else:
            await msg.edit(
                embed=discord.Embed(
                    description=f"{username}'s rank was changed from {from_rank} to {to_rank}.",
                    color=discord.Color.red()
                )
            )


    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def promote(self, ctx, username):
        msg = await ctx.reply(
            embed=discord.Embed(
                description="Sending promote command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g promote " + username)
        try:
            username, from_rank, to_rank = await self.bot.wait_for(
                "hypixel_guild_member_promote",
                check=lambda p, f, t: p.lower() == username.lower(),
                timeout=5
            )
        except asyncio.TimeoutError:
            await msg.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was promoted.",
                    color=discord.Color.red()
                )
            )
        else:
            await msg.edit(
                embed=discord.Embed(
                    description=f"Promoted {username} from {from_rank} to {to_rank}.",
                    color=discord.Color.green()
                )
            )

    @commands.command()
    @commands.has_role(DiscordConfig.commandRole)
    async def demote(self, ctx, username):
        msg = await ctx.reply(
            embed=discord.Embed(
                description="Sending demote command...",
                color=discord.Color.gold()
            )
        )
        await self.bot.mineflayer_bot.chat("/g demote " + username)
        try:
            username, from_rank, to_rank = await self.bot.wait_for(
                "hypixel_guild_member_demote",
                check=lambda p, f, t: p.lower() == username.lower(),
                timeout=5
            )
        except asyncio.TimeoutError:
            await msg.edit(
                embed=discord.Embed(
                    description=f"Could not confirm if {username} was demoted.",
                    color=discord.Color.red()
                )
            )
        else:
            await msg.edit(
                embed=discord.Embed(
                    description=f"Demoted {username} from {from_rank} to {to_rank}.",
                    color=discord.Color.red()
                )
            )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def online(self, ctx):
        await self.bot.mineflayer_bot.chat("/g online")
        if DiscordConfig.officerChannel == ctx.channel.id:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"Sent the `/guild online` command. Output will appear in <#{DiscordConfig.channel}>.",
                    color=discord.Color.blurple()
                ),
                delete_after=10,
            )

    @commands.command(name="list")
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def _list(self, ctx):
        await self.bot.mineflayer_bot.chat("/g list")
        if DiscordConfig.officerChannel == ctx.channel.id:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"Sent the `/guild list` command. Output will appear in <#{DiscordConfig.channel}>.",
                    color=discord.Color.blurple()
                ),
                delete_after=10,
            )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def top(self, ctx, date_int = 0):
        if date_int <= self.date_limit and date_int >= 0:
            await self.bot.mineflayer_bot.chat(f"/g top {date_int}")
            if DiscordConfig.officerChannel == ctx.channel.id:
                await ctx.reply(
                    embed=discord.Embed(
                        description=f"Sent the `/guild top` command. Output will appear in <#{DiscordConfig.channel}>.",
                        color=discord.Color.blurple()
                    ),
                    delete_after=10,
                )
        else:
            embed = discord.Embed(
                description="Can only view 30 days of history.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    async def info(self, ctx):
        await self.bot.mineflayer_bot.chat("/g info")
        if DiscordConfig.officerChannel == ctx.channel.id:
            await ctx.reply(
                embed=discord.Embed(
                    description=f"Sent the `/guild info` command. Output will appear in <#{DiscordConfig.channel}>.",
                    color=discord.Color.blurple()
                ),
                delete_after=10,
            )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.has_role(DiscordConfig.commandRole)
    async def log(self, ctx, *, params: str = ""):
        if DiscordConfig.officerChannel is not None and ctx.channel.id != DiscordConfig.officerChannel:
            embed = discord.Embed(
                description=f"The log command must be used in the officer channel: <#{DiscordConfig.officerChannel}>.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        await self.bot.mineflayer_bot.chat("/g log " + params)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
        elif isinstance(error, (commands.CheckFailure, commands.CheckAnyFailure)):
            embed = discord.Embed(
                description="You do not have permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description="You are missing a required argument: `" + error.param.name + "`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                description="Invalid argument: " + str(error),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
        else:
            await self.bot.send_debug_message(
                f"An error occurred in {ctx.command.name}\n\n"
                f"```py\n"
                f"{''.join(traceback.format_exception(type(error), error, error.__traceback__))}\n"
                f"```"
            )
            

async def setup(bot):
    await bot.add_cog(Bridge(bot))
