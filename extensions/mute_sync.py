"""
Mute syncing extension

Uses the SkyKings and Hypixel APIs.
"""
import asyncio
import datetime
import traceback

import discord

from core.colors import Color

import aiohttp
from discord.ext import commands
from discord.ext import tasks
from core.config import DiscordConfig, ExtensionConfig, ConfigKey, HypixelAPIConfig, SkyKingsConfig


class MuteSyncConfig(ExtensionConfig, base_key="mute_sync"):
    mute_role: int = ConfigKey(int)
    hypixel_api_key: str | None = ConfigKey(str, default=None)
    skykings_api_key: str | None = ConfigKey(str, default=None)


class MuteSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mutes = {}  # (discord id, uuid): datetime
        self.guild_members: set[str] = set()
        self._sess: aiohttp.ClientSession | None = None
        self.mute_task: tuple[asyncio.Task, datetime] | None = None
        self._syncing = False
        self.sync_task.start()
        if MuteSyncConfig.skykings_api_key and not SkyKingsConfig.api_key:
            self.bot.startup_messages.append("[WARNING] Mute Sync: The MUTE_SYNC_SKYKINGS_API_KEY setting is deprecated and may be removed soon. Use SKYKINGS_API_KEY instead.")
            print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > {Color.YELLOW}[WARNING]{Color.RESET} MUTE_SYNC_SKYKINGS_API_KEY is deprecated, use SKYKINGS_API_KEY instead.")
        if MuteSyncConfig.hypixel_api_key and not HypixelAPIConfig.key:
            self.bot.startup_messages.append("[WARNING] Mute Sync: The MUTE_SYNC_HYPIXEL_API_KEY setting is deprecated and may be removed soon. Use HYPIXEL_API_KEY instead.")
            print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > {Color.YELLOW}[WARNING]{Color.RESET} MUTE_SYNC_HYPIXEL_API_KEY is deprecated, use HYPIXEL_API_KEY instead.")

    @property
    def hypixel_api_key(self):
        if HypixelAPIConfig.key:
            return HypixelAPIConfig.key
        return MuteSyncConfig.hypixel_api_key

    @property
    def hypixel_api_url(self):
        return HypixelAPIConfig.url

    @property
    def skykings_api_key(self):
        if SkyKingsConfig.api_key:
            return SkyKingsConfig.api_key
        return MuteSyncConfig.skykings_api_key

    @property
    def skykings_api_url(self):
        return SkyKingsConfig.api_url

    async def cog_unload(self) -> None:
        if self._sess is not None:
            await self._sess.close()
        if self.mute_task is not None:
            self.mute_task[0].cancel()
        try:
            await self.mute_task[0]
        except asyncio.CancelledError:
            pass
        self.mutes = {}
        self.sync_task.cancel()

    async def get_session(self):
        if self._sess is None:
            self._sess = aiohttp.ClientSession()
        return self._sess

    async def get_uuid(self, username):
        session = await self.get_session()
        async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as resp:
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            return data["id"]
        return None

    async def get_discord_user(self, uuid):
        session = await self.get_session()
        async with session.get(
                f"{self.skykings_api_url}/user/info?uuid={uuid}",
                headers={"Authorization": self.skykings_api_key},
        ) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            return int(data["data"]["userid"])
        return None

    async def get_minecraft_uuid(self, userid):
        session = await self.get_session()
        async with session.get(
                f"{self.skykings_api_url}/user/info?userid={userid}",
                headers={"Authorization": self.skykings_api_key},
        ) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            return data["data"]["uuid"]
        return None

    async def get_guild_mutes(self):
        # wait for this to be populated
        while self.bot.mineflayer_bot.bot.username is None:
            await asyncio.sleep(.5)
        bot_uuid = await self.get_uuid(self.bot.mineflayer_bot.bot.username)
        session = await self.get_session()
        mute_data = []
        async with session.get(
                f"{self.hypixel_api_url}/guild?player={bot_uuid}",
                headers={"API-Key": self.hypixel_api_key}
        ) as resp:
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            guild = data["guild"]
            if guild is None:
                return []
            self.guild_members = set(member["uuid"] for member in guild["members"])
            for member in guild["members"]:
                uuid = member["uuid"]
                discord_id = await self.get_discord_user(uuid)
                # datetime 0 will always be in the past
                exp = datetime.datetime.fromtimestamp(member.get("mutedTill", 0) / 1000)
                if exp > datetime.datetime.now():
                    mute_data.append({"userid": discord_id, "uuid": uuid, "muted": True, "expires": exp})
                    self.mutes[(discord_id, uuid)] = exp
                else:
                    mute_data.append({"userid": discord_id, "uuid": uuid, "muted": False})
                    if (discord_id, uuid) in self.mutes:
                        self.mutes.pop((discord_id, uuid))
        return mute_data

    async def sync_mutes(self):
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Syncing mutes...")
        mutes = await self.get_guild_mutes()
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Retrieved mutes: {len(mutes)}")
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        role = guild.get_role(MuteSyncConfig.mute_role)
        members = role.members
        role_guild_members = [m for m in members if m.id in [i["userid"] for i in mutes]]
        muted = [i["userid"] for i in mutes if i["muted"]]
        for member in role_guild_members:
            if member.id not in muted:
                await member.remove_roles(role, reason="Guild mute sync")
            else:
                muted.remove(member.id)
        for user in muted:
            member = guild.get_member(user)
            await member.add_roles(role, reason="Guild mute sync")
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Mutes have been synced!")

    async def process_new_mute(self, player: str, duration: datetime.timedelta):
        uuid = await self.get_uuid(player)
        discord_id = await self.get_discord_user(uuid)
        if discord_id is None:
            return
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        member = guild.get_member(discord_id)
        if member is None:
            return
        self.mutes[(discord_id, uuid)] = datetime.datetime.now() + duration
        await self.update_mute_task()
        role = guild.get_role(MuteSyncConfig.mute_role)
        await member.add_roles(role, reason="User has been guild muted")
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Added mute role to {discord_id}")

    async def process_new_unmute(self, player: str):
        uuid = await self.get_uuid(player)
        # remove mute from self.mutes
        val = [(discord_id, uuid, self.mutes.pop((discord_id, uuid))) for discord_id, _uuid in dict(self.mutes) if
               _uuid == uuid][0]
        discord_id, uuid, exp = val
        if discord_id is None:
            discord_id = await self.get_discord_user(uuid)
            if discord_id is None:
                return
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        member = guild.get_member(discord_id)
        if member is None:
            return
        await self.update_mute_task()
        role = guild.get_role(MuteSyncConfig.mute_role)
        await member.remove_roles(role, reason="User has been guild unmuted")
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Removed mute role from {discord_id}")

    async def _mute_task(self, identifier, expiry):
        try:
            await asyncio.sleep((expiry - datetime.datetime.now()).total_seconds())
            self.mute_task = None
            guild = self.bot.get_channel(DiscordConfig.channel).guild
            member = guild.get_member(identifier[0])
            if member is None:
                return
            role = guild.get_role(MuteSyncConfig.mute_role)
            await member.remove_roles(role, reason="User's guild mute has expired")
            self.mutes.pop(identifier)
            print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Removed mute role from {identifier[0]}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Error in mute task: {e}")
            await self.bot.on_error("mute_task")

    async def update_mute_task(self):
        # take the soonest to expire mute
        if not self.mutes:
            if self.mute_task is not None:
                self.mute_task[0].cancel()
                self.mute_task = None
            return
        [identifier, expiry] = min(self.mutes.items(), key=lambda x: x[1])
        if self.mute_task is not None:
            if expiry < self.mute_task[1]:
                self.mute_task[0].cancel()
                self.mute_task = (asyncio.create_task(self._mute_task(identifier, expiry)), expiry)
        else:
            self.mute_task = (asyncio.create_task(self._mute_task(identifier, expiry)), expiry)
        self.mute_task[0].add_done_callback(lambda _: asyncio.create_task(self.update_mute_task()))

    @commands.Cog.listener()
    async def on_hypixel_guild_member_muted(self, _, player, duration):
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Received mute for {player} for {duration}")
        # hypixel does not allow specific durations (e.g. 1d 1h, only 1h or 1d)
        if duration[-1] == "d":
            delta = datetime.timedelta(days=int(duration[:-1]))
        elif duration[-1] == "h":
            delta = datetime.timedelta(hours=int(duration[:-1]))
        elif duration[-1] == "m":
            delta = datetime.timedelta(minutes=int(duration[:-1]))
        else:
            raise Exception("Invalid duration")
        await self.process_new_mute(player, delta)

    @commands.Cog.listener()
    async def on_hypixel_guild_member_unmuted(self, _, player):
        print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Received unmute for {player}")
        # hypixel does not allow specific durations (e.g. 1d 1h, only 1h or 1d)
        await self.process_new_unmute(player)

    @commands.Cog.listener()
    async def on_hypixel_guild_member_join(self, player):
        uuid = await self.get_uuid(player)
        self.guild_members.add(uuid)

    @commands.Cog.listener()
    async def on_hypixel_guild_member_leave(self, player):
        uuid = await self.get_uuid(player)
        if uuid in self.guild_members:
            self.guild_members.remove(uuid)

    @tasks.loop(hours=12)
    async def sync_task(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        if self.bot.mineflayer_bot is None or not self.bot.mineflayer_bot.is_ready():
            await asyncio.sleep(.5)
        if not self._syncing:
            self._syncing = True
            await self.sync_mutes()
            self._syncing = False

    @sync_task.error
    async def on_sync_task_error(self, exc):
        await self.bot.on_error("sync_task")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.id is None:
            return
        # is the user in our guild?
        if member.guild.id != MuteSyncConfig.guild_id:
            return
        # find the mute
        for (discord_id, uuid), expiry in dict(self.mutes).items():
            if discord_id == member.id:
                if expiry > datetime.datetime.now():
                    role = member.guild.get_role(MuteSyncConfig.mute_role)
                    await member.add_roles(role, reason="JOIN: User has an active guild mute")
                    break

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return
        # check if mute is still valid
        valid = False
        # if they have a current mute, they are obviously in our guild
        for (discord_id, uuid), expiry in dict(self.mutes).items():
            if discord_id == after.id:
                if expiry > datetime.datetime.now():
                    valid = True
                    if MuteSyncConfig.mute_role not in [role.id for role in after.roles]:
                        role = after.guild.get_role(MuteSyncConfig.mute_role)
                        await after.add_roles(role, reason="UPDATE: User has an active guild mute")
                        break
        # if they do not, they might be in a different guild. check if they are in our guild
        if not valid:
            if MuteSyncConfig.mute_role in [role.id for role in after.roles]:
                role = after.guild.get_role(MuteSyncConfig.mute_role)
                uuid = await self.get_minecraft_uuid(after.id)
                if uuid is None:
                    # not even verified, shouldn't have role
                    await after.remove_roles(role, reason="UPDATE: User has no active guild mute")
                    return
                if uuid not in self.guild_members:
                    # not in our guild
                    return
                await after.remove_roles(role, reason="UPDATE: User has no active guild mute")


async def setup(bot):
    print(f"{Color.MAGENTA}Mute Sync{Color.RESET} > Extension is loaded!")
    bot.get_intents().members = True
    await bot.add_cog(MuteSync(bot))
