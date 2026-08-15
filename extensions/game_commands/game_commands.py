"""
Adds commands that can be run in-game.

Uses the Hypixel API.
"""

import aiohttp
import asyncio
import traceback
import time
import re

from core.colors import Color

from discord.ext import commands
from core.config import ExtensionConfig, ConfigKey, DiscordConfig, SkyKingsConfig
from discord_extensions.generic import HELP_EMBED

from .slayer_calculators import calculate_slayer_level, get_next_slayer_level, get_kills_needed

from .classavg_calculator import calculate_classavg

from hashlib import sha256


class GameCommandConfig(ExtensionConfig, base_key="game_commands"):
    hypixel_api_key: str = ConfigKey(str)
    enabled_commands: list = ConfigKey(list, default=[], list_type=str)
    use_antispam: bool = ConfigKey(bool, default=False)
    command_cooldown: float = ConfigKey(float, default=5.0)  # seconds

PREFIX = DiscordConfig.prefix 

RULE_BREAKER_LABELS = {"macroer": "Macroer", "irl_trader": "IRL Trader", "scammer": "Scammer"}

def _fmt_coins(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:,.2f}K"
    return f"{value:,.0f}"

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
    },
    "ca50": {
        "description": "Get the missing M7 runs for a player to reach Class Average 50.",
        "usage": f"{PREFIX}ca50 [player] [profile] [m<mayor%>] [g<global%>]",
    },
    "networth": {
        "description": "Get the networth of a player.",
        "usage": f"{PREFIX}networth (player) [profile]",
    },
    "nw": {
        "description": "Alias for networth.",
        "usage": f"{PREFIX}nw (player) [profile]",
    },
    "lookup": {
        "description": "Check if a player is on the SkyKings rule breaker list.",
        "usage": f"{PREFIX}lookup (player)",
    },
}

class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        valid_commands = {
            "level": self.level,
            "slayers": self.slayers,
            "ca50": self.ca50,
            "networth": self.networth,
            "nw": self.networth,
            "lookup": self.lookup,
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
            data = await resp.json()
            if resp.status not in (200, 404):
                print(f"{Color.MAGENTA}Game Commands{Color.RESET} > {Color.RED}[ERROR]{Color.RESET} Non-OK response from Hypixel: {data}")
            return data
        
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
        if not profiles:
            return await chat_msg(f"{player} has no profiles.")
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

    async def networth(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)
        if len(args) == 0 and name.startswith("@"):
            return await chat_msg("Must provide player name for Discord commands.")
        player = args.pop(0) if args else name
        profile = args.pop(0) if args else None

        api_key = SkyKingsConfig.api_key
        if not api_key:
            return await chat_msg("A SkyKings API Key is needed for this command.")

        try:
            uuid, player = await self.get_info(player)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await chat_msg(f"{player} does not exist.")
            raise

        # Fetch Hypixel profiles so the API doesn't need to use its own key
        profiles_data = await self.hypixel_request(
            f"https://api.hypixel.net/v2/skyblock/profiles?key={GameCommandConfig.hypixel_api_key}&uuid={uuid}"
        )
        if not profiles_data.get("success"):
            return await chat_msg(f"Failed to get {player}'s SkyBlock profiles.")

        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.post(
                f"{SkyKingsConfig.api_url.rstrip('/')}/networth",
                params={"api_key": api_key},
                json={
                    "profile_data": profiles_data,
                    "uuid": uuid,
                    "name": player,
                    "profile_name": profile,
                    "include_bank": True,
                    "include_museum": False,
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
        except Exception as e:
            return await chat_msg(f"Failed to contact the SkyKings API: {e}")

        if not data.get("success"):
            error_msg = data.get("message") or data.get("error") or "Unknown error"
            return await chat_msg(f"Error: {error_msg}")

        d = data["data"]
        player_name = d["player"]["name"]
        profile_name = d["profile"]["name"]
        nw = _fmt_coins(d["totals"].get("networth", 0))
        await chat_msg(f"{player_name} ({profile_name}): Networth {nw} coins.")

    async def lookup(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)
        if len(args) == 0 and name.startswith("@"):
            return await chat_msg("Must provide a player name for Discord commands.")
        player = args.pop(0) if args else name

        api_key = SkyKingsConfig.api_key
        if not api_key:
            return await chat_msg("A SkyKings API Key is needed for this command.")

        try:
            uuid, player = await self.get_info(player)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await chat_msg(f"{player} does not exist.")
            raise

        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            async with self.session.get(
                f"{SkyKingsConfig.api_url.rstrip('/')}/user/lookup",
                params={"uuid": uuid, "api_key": api_key},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                data = await resp.json()
        except Exception as e:
            return await chat_msg(f"Failed to contact the SkyKings API: {e}")

        if not data.get("success"):
            error_msg = data.get("message") or data.get("error") or "Unknown error"
            return await chat_msg(f"Error: {error_msg}")

        result = data.get("result") or {}
        if not result.get("flagged"):
            return await chat_msg(f"{player} is not on the rule breaker list.")

        category = RULE_BREAKER_LABELS.get(result.get("category"), result.get("category") or "Rule Breaker")
        reason = result.get("reason")
        msg = f"{player} is on the rule breaker list as a {category}."
        if reason:
            msg += f" Reason: {reason}"
        await chat_msg(msg)

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
        if not profiles:
            return await chat_msg(f"{player} has no profiles.")
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
        
    async def ca50(self, name, args, *, officer: bool = False, head: str = None):
        chat_msg = lambda msg: self.send_chat_message(name, msg, officer=officer, head=head)

        args = list(args)

        player_name = None
        if args:
            first = args[0].lower()
            is_first_short_flag = re.fullmatch(r"[mg]\d+(?:\.\d+)?%?", first) is not None
            is_first_keyword = first in ("m", "g", "mayor", "global")
            if not is_first_short_flag and not is_first_keyword:
                player_name = args.pop(0)

        profile_name = None
        if args:
            second = args[0].lower()
            is_second_short_flag = re.fullmatch(r"[mg]\d+(?:\.\d+)?%?", second) is not None
            is_second_keyword = second in ("m", "g", "mayor", "global")
            if not is_second_short_flag and not is_second_keyword:
                profile_name = args.pop(0)

        if player_name is None and name.startswith("@"):
            return await chat_msg("Must provide player name for Discord commands.")
        elif player_name is None:
            player_name = name

        # Boost Parser
        global_boost = 0.0
        mayor_boost = 0.0
        while args:
            current = args.pop(0).lower()

            m_match = re.fullmatch(r"m(\d+(?:\.\d+)?)%?", current)
            g_match = re.fullmatch(r"g(\d+(?:\.\d+)?)%?", current)

            if m_match:
                mayor_boost = float(m_match.group(1)) / 100.0
                continue

            if g_match:
                global_boost = float(g_match.group(1)) / 100.0
                continue

            if current == "mayor":
                if not args:
                    return await chat_msg("Missing mayor boost value.")
                mayor_boost = float(args.pop(0).replace("%", "")) / 100.0
                continue

            if current == "global":
                if not args:
                    return await chat_msg("Missing global boost value.")
                global_boost = float(args.pop(0).replace("%", "")) / 100.0
                continue

            return await chat_msg(f"Unknown argument: '{current}'.")
        
        # API FETCHING
        try:
            uuid, player_name = await self.get_info(player_name)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return await chat_msg(f"{player_name} does not exist.")
            raise
        data = await self.hypixel_request(
            f"https://api.hypixel.net/v2/skyblock/profiles?key={GameCommandConfig.hypixel_api_key}&uuid={uuid}"
        )
        if not data.get("success", False):
            return await chat_msg(f"Failed to get {player_name}'s profile.")
        profiles = data.get("profiles", [])
        if not profiles:
            return await chat_msg(f"{player_name} has no profiles.")

        if profile_name is None:
            selected = [p for p in profiles if p.get("selected")]
            profile_obj = selected[0] if selected else profiles[0]
        else:
            matches = [
                p for p in profiles
                if p.get("cute_name", "").lower() == profile_name.lower()
            ]
            if not matches:
                valid = ", ".join(p.get("cute_name", "Unknown") for p in profiles)
                return await chat_msg(f"Invalid profile: {valid}.")
            profile_obj = matches[0]

        member = profile_obj.get("members", {}).get(uuid)
        if member is None:
            return await chat_msg(f"{player_name} is not in the profile.")

        # Calculation
        result = await calculate_classavg(
            member,
            global_boost=global_boost,
            mayor_boost=mayor_boost,
        )
        order = ["archer", "berserk", "healer", "mage", "tank"]
        details = ", ".join(
            f"{result['runs'][cls]} {cls.capitalize()}"
            for cls in order
            if result["runs"].get(cls, 0) > 0
        )
        if result["total_runs"] == 0:
            return await chat_msg(
                f"{player_name} ({profile_obj['cute_name']}) already has Class Average 50! GG!"
            )
        await chat_msg(
            f"It will take {result['total_runs']:,} M7 runs for {player_name} "
            f"({profile_obj['cute_name']}) to reach Class Average 50 ({details})"
        )