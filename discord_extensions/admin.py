import asyncio
import os

import discord
from discord.ext import commands, tasks
from core.config import DiscordConfig, SettingsConfig

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_bot_status.start()

    @commands.command()
    @commands.has_role(DiscordConfig.overrideRole)
    async def notifications(self, ctx):
        await self.bot.mineflayer_bot.chat("/g notifications")

    @commands.command()
    @commands.has_role(DiscordConfig.overrideRole)
    async def toggleaccept(self, ctx):
        if SettingsConfig.autoaccept:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``off``!")
            await ctx.send(embed=embedVar)
            SettingsConfig.autoaccept = False
        else:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``on``!")
            await ctx.send(embed=embedVar)
            SettingsConfig.autoaccept = True

    @commands.command(aliases=['r'])
    @commands.has_role(DiscordConfig.commandRole)
    async def relog(self, ctx):
        self.bot.mineflayer_bot.stop(True)
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Restarting the bot...")
        await ctx.send(embed=embedVar)

    @commands.command(aliases=['o', 'over'])
    @commands.has_role(DiscordConfig.overrideRole)
    async def override(self, ctx, *, command):
        await self.bot.mineflayer_bot.chat("/" + command)
        embedVar = discord.Embed(color=0x1ABC9C, description=f"`/{command}` has been sent!")
        await ctx.send(embed=embedVar)

    @commands.command()
    @commands.has_role(DiscordConfig.overrideRole)
    async def update(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Updating the bot...")
        await ctx.send(embed=embedVar)
        os.system("git pull")
        await self.bot.close()
        await asyncio.sleep(10)

    @commands.command()
    @commands.has_role(DiscordConfig.overrideRole)
    async def reload(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Reloading extensions...")
        msg = await ctx.send(embed=embedVar)
        os.system("git pull")
        for ext in self.bot.extensions:
            await self.bot.reload_extensions(ext)
        embed = discord.Embed(color=0x1ABC9C).set_author(name="Extensions reloaded!")
        await msg.edit(embed=embed)

    @tasks.loop(seconds=60)
    async def check_bot_status(self):
        try:
            print("AAAAAAAAAAAAAAAA")
            print(self.bot.mineflayer_bot)
            if self.bot.mineflayer_bot is not None:
                print("no")
                print(self.bot.mineflayer_bot.is_online())
                if self.bot.mineflayer_bot.is_online():
                    print("Discord > Bot is online!")
                else:
                    print("Discord > Bot is offline!")
                    await self.bot.close()
                    await asyncio.sleep(10)
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Admin(bot))


