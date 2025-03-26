"""
Adds commands that can be run in-game.

Uses the Hypixel API.
"""

import aiohttp
import asyncio
import traceback
import time

from core.colors import Color

from discord.ext import commands
from core.config import ExtensionConfig, ConfigKey, DiscordConfig
from discord_extensions.generic import HELP_EMBED

from .slayer_calculators import calculate_slayer_level, get_next_slayer_level, get_kills_needed

from hashlib import sha256


class GameCommandConfig(ExtensionConfig, base_key="game_commands"):
    hypixel_api_key: str = ConfigKey(str)
    enabled_commands: list = ConfigKey(list, default=[], list_type=str)
    use_antispam: bool = ConfigKey(bool, default=False)
    command_cooldown: float = ConfigKey(float, default=5.0)  # seconds

PREFIX = DiscordConfig.prefix 

COMMAND_INFO = {
    "help": {
        "description": "Get help on commands.",
        "usage": f"{PREFIX}help [command]",
    },
    "level": {
        "description": "Get the level of a player.",
        "usage": f"{PREFIX}level (player) [profile]",
    },
    "slayers": {
        "description": "Get the slayer levels of a player.",
        "usage": f"{PREFIX}slayers (player) [profile] [boss]",
    }
}

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        valid_commands = {
            "level": self.level,
            "slayers": self.slayers,
        }
        cmd_list = list(GameCommandConfig.enabled_commands)
        if not GameCommandConfig.enabled_commands:
            print(f"{Color.MAGENTA}Game Commands{Color.RESET} > No commands enabled, defaulting to all.")
            cmd_list = list(valid_commands.keys())
        self.commands = {k: v for k, v in valid_commands.items() if k in cmd_list}
        self.commands["help"] = self.help  # always add help command
        for command in cmd_list:
            if command not in self.commands:
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > {Color.YELLOW}[WARNING]{Color.RESET} Command '{command}' is not valid and will be ignored.")
        for command in valid_commands.keys():
            if command not in cmd_list:
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > Command '{command}' is disabled.")
        self.session = None
        self.index = 0
        self.last_command = None
        HELP_EMBED.description += "\n``( )`` = Argument required in Discord, optional in-game"
        HELP_EMBED.insert_field_at(
            2,
            name="Game Commands",
            value="\n".join([f"``{v['usage']}`` {v['description']}" for k, v in COMMAND_INFO.items() if k in cmd_list]),
            inline=False
        )

    @property
    def antispam(self):
        self.index += 1
        return sha256(str(self.index).encode()).hexdigest()[:10]

    async def send_chat_message(self, name, content, *, officer: bool = False, head: str = None):
        cmd = ("/oc " if officer else "/gc ")
        msg = f"[CMD] {name}: {content}"
        if GameCommandConfig.use_antispam:
            msg += f" / {self.antispam}"
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
        await self.bot.send_user_message(name, content, officer=officer, command=True, head=head)

    async def process_command(self, name, message, *, officer: bool = False, head: str = None):
        if self.last_command is not None and time.time() - self.last_command < GameCommandConfig.command_cooldown:
            return
        self.last_command = time.time()
        command = message.split(" ")[0]
        args = message.split(" ")[1:]
        try:
            cmd = self.commands.get(command)
            if cmd:
                await cmd(name, args, officer=officer, head=head)
            else:
                await self.unknown_command(name, args, officer=officer, head=head)
        except Exception as e:
            await self.send_chat_message(name, f"Error processing command '{command}': {str(e)}", officer=officer, head=head)
            print(f"{Color.MAGENTA}Game Commands{Color.RESET} > {Color.RED}[ERROR]{Color.RESET} Error processing command '{command}' from {name}: {e}")
            tb = traceback.format_exc()
            for line in tb.splitlines():
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > {Color.RED}[ERROR]{Color.RESET} {line}")

    @commands.Cog.listener()
    async def on_hypixel_guild_message(self, name, message, *, head: str = None):
        if not message.startswith(PREFIX):
            return
        await self.process_command(name, message[1:], head=head)

    @commands.Cog.listener()
    async def on_hypixel_guild_officer_message(self, name, message, *, head: str = None):
        if not message.startswith(PREFIX):
            return
        await self.process_command(name, message[1:], officer=True, head=head)

    # discord invocation
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            if ctx.channel.id == DiscordConfig.channel:
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > Invoking from Discord")
                await self.on_hypixel_guild_message("@" + ctx.author.name, ctx.message.content, head=ctx.author.display_avatar.url)
            elif ctx.channel.id == DiscordConfig.officerChannel:
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > Invoking from Discord")
                await self.on_hypixel_guild_officer_message("@" + ctx.author.name, ctx.message.content, head=ctx.author.display_avatar.url)
            
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
        for i, field in enumerate(HELP_EMBED.fields):
            if field.name == "Game Commands":
                HELP_EMBED.remove_field(i)
                break
        # remove line from description
        HELP_EMBED.description = "\n".join([line for line in HELP_EMBED.description.splitlines() if not line == "``( )`` = Argument required in Discord, optional in-game"])

    async def get_info(self, username):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        async with self.session.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{username}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["id"], data["name"]

    # commands
    async def unknown_command(self, name, args, *, officer: bool = False, head: str = None):
        return
    
    async def help(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)
        if len(args) == 0:
            return await chat_msg("Commands: " + ", ".join([PREFIX + k for k in self.commands.keys()]))
        command = args[0]
        if command not in self.commands:
            return await chat_msg(f"Unknown command: {command}.")
        if command in COMMAND_INFO:
            return await chat_msg(f"{COMMAND_INFO[command]['usage']} - {COMMAND_INFO[command]['description']}")
        return await chat_msg(f"Command '{command}' does not have help information.")

    async def level(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)
        if len(args) == 0 and name.startswith("@"):
            return await chat_msg(f"Must provide player name for Discord commands.")
        player = args.pop(0) if args else name
        profile = args.pop(0) if args else None
        try:
            uuid, player = await self.get_info(player)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await chat_msg(f"{player} does not exist.")
            raise
        data = await self.hypixel_request(f"https://api.hypixel.net/v2/skyblock/profiles?key={GameCommandConfig.hypixel_api_key}&uuid={uuid}")
        if not data["success"]:
            return await chat_msg(f"Failed to get {player}'s profile.")
        profiles = data["profiles"]
        if profile is None:
            profile = [p for p in profiles if p.get("selected")]
            if not profile:
                profile = profiles
            profile = profile[0]
        else:
            profile = [p for p in profiles if p["cute_name"].lower() == profile.lower()]
            if not profile:
                return await chat_msg(f"Invalid profile: {', '.join([p['cute_name'] for p in profiles])}.")
            profile = profile[0]
        member = profile["members"].get(uuid)
        if member is None:
            return await chat_msg(f"{player} is not in the profile.")
        xp = member.get("leveling", {}).get("experience", 0)
        level, extra = divmod(xp, 100)
        await chat_msg(f"{player} ({profile['cute_name']}): Level {level:,}, {extra}/100 xp to next level.")
    
    async def slayers(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)
        if len(args) == 0 and name.startswith("@"):
            return await chat_msg(f"Must provide player name for Discord commands.")
        player = args.pop(0) if args else name
        profile = args.pop(0) if args else None
        selected_slayer = args.pop(0).lower() if args else None
        bosses = ["zombie", "spider", "wolf", "enderman", "blaze", "vampire"]
        if profile in bosses:
            selected_slayer = profile
            profile = None
        try:
            uuid, player = await self.get_info(player)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await chat_msg(f"{player} does not exist.")
            raise
        data = await self.hypixel_request(f"https://api.hypixel.net/v2/skyblock/profiles?key={GameCommandConfig.hypixel_api_key}&uuid={uuid}")
        if not data["success"]:
            return await chat_msg(f"Failed to get {player}'s profile.")
        profiles = data["profiles"]
        if profile is None:
            profile = [p for p in profiles if p.get("selected")]
            if not profile:
                profile = profiles
            profile = profile[0]
        else:
            profile = [p for p in profiles if p["cute_name"].lower() == profile.lower()]
            if not profile:
                return await chat_msg(f"Invalid profile: {', '.join([p['cute_name'] for p in profiles])}.")
            profile = profile[0]
        member = profile["members"].get(uuid)
        if member is None:
            return await chat_msg(f"{player} is not in the profile.")
        slayers = member.get("slayer", {}).get("slayer_bosses")
        if slayers is None:
            return await chat_msg(f"{player} has no slayer data")
        if selected_slayer is None:
            message = f"{player} ({profile['cute_name']}): "
            boss_text = []
            for boss in bosses:
                if boss not in slayers:
                    continue
                xp = slayers[boss].get("xp", 0)
                level = calculate_slayer_level(boss, xp)
                boss_text.append(f"{boss.capitalize()} {int(level)} ({xp:,} xp)")
            if not boss_text:
                return await chat_msg(f"{player} has no slayer data")
            message += " / ".join(boss_text)
            return await chat_msg(message)
        else:
            if selected_slayer not in bosses:
                return await chat_msg(f"Invalid slayer: {', '.join(bosses)}.")
            boss = selected_slayer
            boss_data = slayers.get(selected_slayer)
            if boss_data is None:
                return await chat_msg(f"{player} has no data for {selected_slayer.capitalize()}.")
            message = f"{player} ({profile['cute_name']}): "
            xp = boss_data.get("xp", 0)
            level = calculate_slayer_level(boss, xp)
            next_level, xp_needed = get_next_slayer_level(selected_slayer, xp)
            if next_level is None:
                message += f"{selected_slayer.capitalize()} {int(level)} ({xp:,} xp) - Max level reached"
            else:
                message += f"{selected_slayer.capitalize()} {int(level)} ({xp:,} xp) - Next level in {xp_needed:,} xp (Kills: "
                kills_needed = get_kills_needed(selected_slayer, xp_needed)
                kn = []
                for tier, kills in enumerate(kills_needed):
                    kn.append(f"{kills:,} T{tier+1}")
                message += " / ".join(kn) + ")"
            return await chat_msg(message)
