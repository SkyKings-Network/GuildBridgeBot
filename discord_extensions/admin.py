import asyncio
import os

import discord
from discord.ext import commands, tasks
from core.config import DiscordConfig, SettingsConfig, DataConfig, ServerConfig, AccountConfig, RedisConfig
from core.checks import has_override_role, has_command_role

import json
import aiohttp
from datetime import datetime


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_bot_status.start()

    @commands.command()
    @has_override_role
    async def notifications(self, ctx):
        await self.bot.mineflayer_bot.chat("/g notifications")

    @commands.command()
    @has_override_role
    async def toggleaccept(self, ctx):
        if SettingsConfig.autoaccept:
            embedVar = discord.Embed(
                description=":white_check_mark: Auto accepting guild join requests is now ``off``!"
                )
            SettingsConfig.autoaccept = False
        else:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild join requests is now ``on``!")
            SettingsConfig.autoaccept = True
        await ctx.send(embed=embedVar)

    @commands.command()
    async def toggleinvites(self, ctx):
        """Toggle hiding of guild invite messages (Owner only)"""
        if not await ctx.bot.is_owner(ctx.author):
            embedVar = discord.Embed(
                color=discord.Color.red(),
                description=":x: This command can only be used by the bot owner!"
            )
            await ctx.send(embed=embedVar)
            return

        if SettingsConfig.hideInviteMessages:
            embedVar = discord.Embed(
                description=":white_check_mark: Guild invite messages will now be ``shown``!"
            )
            SettingsConfig.hideInviteMessages = False
        else:
            embedVar = discord.Embed(
                description=":white_check_mark: Guild invite messages will now be ``hidden``!"
            )
            SettingsConfig.hideInviteMessages = True
        
        await ctx.send(embed=embedVar)
        

    @commands.command(aliases=['r'])
    @has_command_role
    async def relog(self, ctx):
        embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Restarting the bot...")
        await ctx.send(embed=embedVar)
        try:
            self.bot.mineflayer_bot.stop(True)
        except Exception as e:
            print(e)
            embedVar = discord.Embed(color=0x1ABC9C).set_author(name="Error while restarting the bot!")
            await ctx.send(embed=embedVar)

    @commands.command(aliases=['o', 'over'])
    @has_override_role
    async def override(self, ctx, *, command):
        await self.bot.mineflayer_bot.chat("/" + command)
        embedVar = discord.Embed(color=0x1ABC9C, description=f"`/{command}` has been sent!")
        await ctx.send(embed=embedVar)

    @commands.command(hidden=os.getenv("IS_DOCKER") == 1)
    @has_override_role
    async def update(self, ctx):
        if os.getenv("IS_DOCKER") == "1":
            embedVar = discord.Embed(
                color=discord.Color.red(),
                description=":x: Automatic updating is not supported in Docker deployments!\n"
                            "Instead, you will need to run these commands in your bridge bot server's terminal:\n"
                            "```sh\n"
                            "docker compose -f compose.yml pull\n"
                            "docker compose -f compose.yml up -d\n"
                            "```"
            )
            await ctx.send(embed=embedVar)
            return
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
        if os.getenv("IS_DOCKER") != "1":
            os.system("git pull")
        for ext in list(self.bot.extensions):
            await self.bot.reload_extension(ext)
        embed = discord.Embed(color=0x1ABC9C).set_author(name="Extensions reloaded!")
        await msg.edit(embed=embed)

    @commands.command()
    async def config(self, ctx):
        """Shows current configuration settings (Owner only)"""
        if not await ctx.bot.is_owner(ctx.author):
            embedVar = discord.Embed(
                color=discord.Color.red(),
                description=":x: This command can only be used by the bot owner!"
            )
            await ctx.send(embed=embedVar)
            return

        embedVar = discord.Embed(
            title="⚙️ Bot Configuration",
            color=0x1ABC9C,
            timestamp=discord.utils.utcnow()
        )

        # Server Config
        embedVar.add_field(
            name="🖥️ Server",
            value=f"**Host:** `{ServerConfig.host}`\n**Port:** `{ServerConfig.port}`",
            inline=False
        )

        # Discord Config (hide sensitive data)
        discord_info = (
            f"**Channel:** <#{DiscordConfig.channel}>\n"
            f"**Officer Channel:** {f'<#{DiscordConfig.officerChannel}>' if DiscordConfig.officerChannel else '`Not set`'}\n"
            f"**Command Role:** <@&{DiscordConfig.commandRole}>\n"
            f"**Override Role:** <@&{DiscordConfig.overrideRole}>\n"
            f"**Prefix:** `{DiscordConfig.prefix}`\n"
            f"**Webhook:** `{'✅ Configured' if DiscordConfig.webhookURL else '❌ Not set'}`\n"
            f"**Officer Webhook:** `{'✅ Configured' if DiscordConfig.officerWebhookURL else '❌ Not set'}`\n"
            f"**Debug Webhook:** `{'✅ Configured' if DiscordConfig.debugWebhookURL else '❌ Not set'}`"
        )
        embedVar.add_field(
            name="💬 Discord",
            value=discord_info,
            inline=False
        )

        # Redis Config
        redis_status = "✅ Enabled" if RedisConfig.host else "❌ Disabled"
        redis_info = f"**Status:** `{redis_status}`"
        if RedisConfig.host:
            redis_info += (
                f"\n**Host:** `{RedisConfig.host}`\n"
                f"**Port:** `{RedisConfig.port}`\n"
                f"**Client Name:** `{RedisConfig.clientName or 'Not set'}`"
            )
        embedVar.add_field(
            name="🔴 Redis",
            value=redis_info,
            inline=False
        )

        # Settings Config
        settings_info = (
            f"**Auto Accept:** `{'✅ On' if SettingsConfig.autoaccept else '❌ Off'}`\n"
            f"**Date Limit:** `{SettingsConfig.dateLimit} days`\n"
            f"**Print Chat:** `{'✅ On' if SettingsConfig.printChat else '❌ Off'}`\n"
            f"**Hide Invite Messages:** `{'✅ On' if SettingsConfig.hideInviteMessages else '❌ Off'}`\n"
            f"**Extensions:** `{len(SettingsConfig.extensions)} loaded`"
        )
        embedVar.add_field(
            name="⚙️ Settings",
            value=settings_info,
            inline=False
        )

        # Data Config
        if DataConfig.current_version:
            embedVar.add_field(
                name="📊 Version Info",
                value=f"**Current:** `{DataConfig.current_version}`",
                inline=False
            )

        embedVar.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embedVar)

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


async def setup(bot):
    await bot.add_cog(Admin(bot))
