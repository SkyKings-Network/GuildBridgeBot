import asyncio
import os

import discord
from discord.ext import commands, tasks
from core.config import DiscordConfig, SettingsConfig, DataConfig
from core.checks import has_override_role, has_command_role

import json
import aiohttp
from datetime import datetime

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_bot_status.start()
        self.check_bot_version.start()

    @commands.command()
    @has_override_role
    async def notifications(self, ctx):
        await self.bot.mineflayer_bot.chat("/g notifications")

    @commands.command()
    @has_override_role
    async def toggleaccept(self, ctx):
        if SettingsConfig.autoaccept:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild join requests is now ``off``!")
            await ctx.send(embed=embedVar)
            SettingsConfig.autoaccept = False
        else:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild join requests is now ``on``!")
            await ctx.send(embed=embedVar)
            SettingsConfig.autoaccept = True

    @commands.command(aliases=['r'])
    @has_command_role
    async def relog(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Restarting the bot...")
        await ctx.send(embed=embedVar)
        await self.bot.loop.run_in_executor(None, self.bot.mineflayer_bot.stop, True)

    @commands.command(aliases=['o', 'over'])
    @has_override_role
    async def override(self, ctx, *, command):
        await self.bot.mineflayer_bot.chat("/" + command)
        embedVar = discord.Embed(color=0x1ABC9C, description=f"`/{command}` has been sent!")
        await ctx.send(embed=embedVar)

    @commands.command()
    @has_override_role
    async def update(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Updating the bot...")
        await ctx.send(embed=embedVar)
        url = "https://api.github.com/repos/SkyKings-Network/GuildBridgeBot/commits/main"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    latest_commit_date = data["commit"]["committer"]["date"]
                    latest_commit_date = datetime.strptime(latest_commit_date, "%Y-%m-%dT%H:%M:%SZ")

                    with open("config.json", "r") as f:
                        config = json.load(f)
                    
                    config["data"]["current_version"] = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                    config["data"]["latest_version"] = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")

                    with open("config.json", "w") as f:
                        json.dump(config, f, indent=4)
                    
                    DataConfig.current_version = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                    DataConfig.latest_version = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                        
                    
                    print(f"Updated config.json with latest commit date: {latest_commit_date}")
                else:
                    print(f"Failed to check for updates. HTTP Status: {response.status}")

        os.system("git pull")
        await self.bot.close()
        await asyncio.sleep(10)

    @commands.command()
    @has_override_role
    async def reload(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Reloading extensions...")
        msg = await ctx.send(embed=embedVar)
        os.system("git pull")
        for ext in list(self.bot.extensions):
            await self.bot.reload_extension(ext)
        embed = discord.Embed(color=0x1ABC9C).set_author(name="Extensions reloaded!")
        await msg.edit(embed=embed)

    @tasks.loop(seconds=60)
    async def check_bot_status(self):
        try:
            if self.bot.mineflayer_bot is not None:
                if self.bot.mineflayer_bot.is_online() or self.bot.mineflayer_bot.is_starting():
                    pass
                else:
                    print("Discord > Bot is offline!")
                    await self.bot.close()
                    await asyncio.sleep(10)
        except Exception as e:
            print(e)

    @tasks.loop(seconds=600)
    async def check_bot_version(self):
        try:
            await self.bot.wait_until_ready()
            
            config_current_commit_date = DataConfig.current_version

            url = "https://api.github.com/repos/SkyKings-Network/GuildBridgeBot/commits/main"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        latest_commit_date = data["commit"]["committer"]["date"]
                        latest_commit_date = datetime.strptime(latest_commit_date, "%Y-%m-%dT%H:%M:%SZ")

                        if config_current_commit_date == "":
                            print(f"Set version in config.json to the current commit date. {latest_commit_date}")
                            DataConfig.current_version = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                            return

                        config_current_commit_date = datetime.strptime(config_current_commit_date, "%Y-%m-%dT%H:%M:%SZ")

                        # Check if the latest commit date is greater than the current commit date
                        if latest_commit_date > config_current_commit_date:
                            with open("config.json", "r") as f:
                                config = json.load(f)
                            
                            config["data"]["latest_version"] = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")

                            with open("config.json", "w") as f:
                                json.dump(config, f, indent=4)

                            DataConfig.latest_version = latest_commit_date.strftime("%Y-%m-%dT%H:%M:%SZ")

                    else:
                        print(f"Failed to check for updates. HTTP Status: {response.status}")

            
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(Admin(bot))


