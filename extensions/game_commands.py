"""
Adds commands that can be run in-game.

Uses the Hypixel API.
"""

import aiohttp
import asyncio

from discord.ext import commands
from core.config import ExtensionConfig, ConfigKey

from hashlib import sha256


class GameCommandConfig(ExtensionConfig, base_key="game_commands"):
    hypixel_api_key: str = ConfigKey(str)


class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands = {
            "help": self.help,
            "level": self.level,
        }
        self.session = None
        self.index = 0

    @property
    def antispam(self):
        self.index += 1
        return sha256(str(self.index).encode()).hexdigest()[:10]

    async def send_chat_message(self, name, content, *, officer: bool = False):
        cmd = ("/oc " if officer else "/gc ")
        msg = f"[CMD] {name}: {content} / {self.antispam}"
        await self.bot.mineflayer_bot.chat(cmd + msg)
        try:
            await self.bot.wait_for("hypixel_guild_message_send_failed", timeout=1)
            print("Command output blocked.")
        except asyncio.TimeoutError:
            pass
        else:
            while True:
                await self.bot.mineflayer_bot.chat(cmd + "Output blocked, check Discord. / " + self.antispam)
                try:
                    await self.bot.wait_for("hypixel_guild_message_send_failed", timeout=1)
                except asyncio.TimeoutError:
                    break
        await self.bot.send_user_message(name, content, officer=officer, command=True)

    async def process_command(self, name, message, *, officer: bool = False):
        command = message.split(" ")[0]
        args = message.split(" ")[1:]
        await self.commands.get(command, self.unknown_command)(name, args, officer=officer)

    @commands.Cog.listener()
    async def on_hypixel_guild_message(self, name, message):
        if not message.startswith("!"):
            return
        await self.process_command(name, message[1:])

    @commands.Cog.listener()
    async def on_hypixel_guild_officer_message(self, name, message):
        if not message.startswith("!"):
            return
        await self.process_command(name, message[1:], officer=True)

    async def hypixel_request(self, *args, **kwargs):
        if "headers" not in kwargs:  
            kwargs["headers"] = {"API-Key": GameCommandConfig.hypixel_api_key}
        if self.session is None:
            self.session = aiohttp.ClientSession()
        async with self.session.get(*args, **kwargs) as resp:
            return await resp.json()
        
    async def cog_unload(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def get_info(self, username):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        async with self.session.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{username}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["id"], data["name"]

    # commands
    async def unknown_command(self, name, args, *, officer: bool = False):
        return
    
    async def help(self, name, args, *, officer: bool = False):
        await self.send_chat_message(name, "Commands: " + ", ".join(["!" + k for k in self.commands.keys()]), officer=officer)

    async def level(self, name, args, *, officer: bool = False):
        if len(args) < 1:
            return await self.send_chat_message(name, "Usage: !level <player> [profile]", officer=officer)
        player = args[0]
        profile = args[1] if len(args) > 1 else None
        try:
            uuid, player = await self.get_info(player)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await self.send_chat_message(name, f"{player} does not exist.", officer=officer)
            raise
        data = await self.hypixel_request(f"https://api.hypixel.net/v2/skyblock/profiles?key={GameCommandConfig.hypixel_api_key}&uuid={uuid}")
        if not data["success"]:
            return await self.send_chat_message(name, f"Failed to get {player}'s profile.", officer=officer)
        profiles = data["profiles"]
        if profile is None:
            profile = [p for p in profiles if p.get("selected")]
            if not profile:
                profile = profiles
            profile = profile[0]
        else:
            profile = [p for p in profiles if p["cute_name"].lower() == profile.lower()]
            if not profile:
                return await self.send_chat_message(name, f"Invalid profile: {', '.join([p['cute_name'] for p in profiles])}.", officer=officer)
            profile = profile[0]
        member = profile["members"].get(uuid)
        if member is None:
            return await self.send_chat_message(name, f"{player} is not in the profile.", officer=officer)
        xp = member.get("leveling", {}).get("experience", 0)
        level, extra = divmod(xp, 100)
        await self.send_chat_message(name, f"{player} ({profile['cute_name']}): Level {level:,}, {extra}/100 xp to next level.", officer=officer)
    


async def setup(bot):
    await bot.add_cog(GameCommands(bot))
