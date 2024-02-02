import asyncio
import os

import discord
from discord.ext import commands
from core.config import discord as config, settings


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_role(config.overrideRole)
    async def notifications(self, ctx):
        self.bot.mineflayer_bot.chat("/g notifications")

    @commands.command()
    @commands.has_role(config.overrideRole)
    async def toggleaccept(self, ctx):
        if settings.autoaccept:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``off``!")
            await ctx.send(embed=embedVar)
            settings.autoaccept = False
        else:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``on``!")
            await ctx.send(embed=embedVar)
            settings.autoaccept = True

    @commands.command(aliases=['r'])
    @commands.has_role(config.commandRole)
    async def relog(self, ctx):
        self.bot.mineflayer_bot.quit()
        embedVar = discord.Embed(description="Restarting the bot...")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=['o', 'over'])
    @commands.has_role(config.overrideRole)
    async def override(self, ctx, *, command):
        self.bot.mineflayer_bot.chat("/" + command)
        embedVar = discord.Embed(description=f"``/{command}`` has been sent!", colour=0x1ABC9C)
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(config.overrideRole)
    async def update(self, ctx):
        embedVar = discord.Embed(description=":white_check_mark: Rebooting Bot...")
        await ctx.send(embed=embedVar)
        os.system("git pull")
        await self.bot.close()

    @commands.command()
    @commands.has_role(config.overrideRole)
    async def reload(self, ctx):
        embedVar = discord.Embed(description="Reloading extensions...")
        msg = await ctx.send(embed=embedVar)
        os.system("git pull")
        for ext in self.bot.extensions:
            await self.bot.reload_extensions(ext)
        embed = discord.Embed(description=":white_check_mark: Extensions reloaded!")
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))


