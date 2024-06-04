"""
Mute syncing extension

Uses the SkyKings and Hypixel APIs.
"""
import asyncio
import datetime

import aiohttp
import discord
from discord.ext import commands
from core.config import DiscordConfig, ExtensionConfig, ConfigKey


class MuteSyncConfig(ExtensionConfig, base_key="mute_sync"):
    mute_role: int = ConfigKey(int)
    hypixel_api_key: str = ConfigKey(str)
    skykings_api_key: str = ConfigKey(str)


class MuteSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mutes = {}  # (discord id, uuid): datetime
        self._sess: aiohttp.ClientSession | None = None
        self.mute_task: tuple[asyncio.Task, datetime] | None = None
        self._syncing = False

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

    async def get_discord_user(self, uuid):
        session = await self.get_session()
        async with session.get(
                f"https://skykings.net/api/user?uuid={uuid}",
                headers={"Authorization": MuteSyncConfig.skykings_api_key},
        ) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            return int(data["user"])

    async def fill_guild_mutes(self):
        bot_uuid = await self.get_uuid(self.bot.mineflayer_bot.bot.username)
        session = await self.get_session()
        async with session.get(
                f"https://api.hypixel.net/guild?player={bot_uuid}",
                headers={"API-Key": MuteSyncConfig.hypixel_api_key}
        ) as resp:
            if resp.status != 200:
                resp.raise_for_status()
            data = await resp.json()
            guild = data["guild"]
            for member in guild["members"]:
                if member.get("mutedTill") is not None:
                    uuid = member["uuid"]
                    discord_id = await self.get_discord_user(uuid)
                    exp = datetime.datetime.fromtimestamp(member["mutedTill"] / 1000)
                    if exp > datetime.datetime.now():
                        self.mutes[(discord_id, uuid)] = exp

    async def sync_mutes(self):
        await self.fill_guild_mutes()
        for (discord_id, uuid), expiry in dict(self.mutes).items():
            if expiry > datetime.datetime.now():
                # use bridge channel to get guild
                guild = self.bot.get_channel(DiscordConfig.channel).guild
                member = guild.get_member(discord_id)
                if member is None:
                    continue
                role = guild.get_role(MuteSyncConfig.mute_role)
                await member.add_roles(role, reason="SYNC: User has an active guild mute")
            elif discord_id is not None:
                guild = self.bot.get_channel(DiscordConfig.channel).guild
                member = guild.get_member(discord_id)
                if member is None:
                    self.mutes.pop((discord_id, uuid))
                    continue
                role = guild.get_role(MuteSyncConfig.mute_role)
                await member.remove_roles(role, reason="SYNC: User has no active guild mute")
                self.mutes.pop((discord_id, uuid))

    async def process_new_mute(self, player: str, duration: datetime.timedelta):
        uuid = await self.get_uuid(player)
        discord_id = await self.get_discord_user(uuid)
        if discord_id is None:
            return
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        member = guild.get_member(discord_id)
        if member is None:
            return
        role = guild.get_role(MuteSyncConfig.mute_role)
        await member.add_roles(role, reason="User has been guild muted")
        self.mutes[(discord_id, uuid)] = datetime.datetime.now() + duration
        await self.update_mute_task()

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
        role = guild.get_role(MuteSyncConfig.mute_role)
        await member.remove_roles(role, reason="User has been guild unmuted")
        await self.update_mute_task()

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
        except asyncio.CancelledError:
            pass
        except Exception as e:
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
        # hypixel does not allow specific durations (e.g. 1d 1h, only 1h or 1d)
        await self.process_new_unmute(player)

    @commands.Cog.listener()
    async def on_minecraft_ready(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_channel(DiscordConfig.channel).guild
        await guild.chunk(cache=True)
        if not self._syncing:
            self._syncing = True
            print("MuteSync > Syncing mutes...")
            await self.sync_mutes()
            # go through role members and check if they are muted
            role = guild.get_role(MuteSyncConfig.mute_role)
            for member in role.members:
                data = [(k, v) for k, v in dict(self.mutes).items() if k[0] == member.id]
                if not data:
                    await member.remove_roles(role, reason="STARTUP: User has no active guild mute")
                else:
                    if data[0][1] < datetime.datetime.now():
                        await member.remove_roles(role, reason="STARTUP: User has no active guild mute")
            print("MuteSync > Mutes synced!")
            self._syncing = False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.id is None:
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
        if (MuteSyncConfig.mute_role in [role.id for role in before.roles] or
                MuteSyncConfig.mute_role in [role.id for role in after.roles]):
            return
        # check if mute is still valid
        valid = False
        for (discord_id, uuid), expiry in dict(self.mutes).items():
            if discord_id == after.id:
                if expiry > datetime.datetime.now():
                    valid = True
                    if MuteSyncConfig.mute_role not in [role.id for role in after.roles]:
                        role = after.guild.get_role(MuteSyncConfig.mute_role)
                        await after.add_roles(role, reason="UPDATE: User has an active guild mute")
                        break
        if not valid:
            if MuteSyncConfig.mute_role in [role.id for role in after.roles]:
                role = after.guild.get_role(MuteSyncConfig.mute_role)
                await after.remove_roles(role, reason="UPDATE: User has no active guild mute")


async def setup(bot):
    bot.get_intents().members = True
    await bot.add_cog(MuteSync(bot))
