import asyncio
import os
import re
import threading
import traceback

import discord
from discord import Embed
from discord.ext import commands

from core.config import discord as discord_config, redis as redis_config
from core.minecraft_bot import MinecraftBotManager
from core.redis_handler import RedisManager

regex = re.compile(r"Guild > ([\[\]+ a-zA-Z0-9_]+): (.+)")
regex_officer = re.compile(r"Officer > ([\[\]+ a-zA-Z0-9_]+): (.+)")


class DiscordBridgeBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(discord_config.prefix), case_insensitive=True,
            allowed_mentions=discord.AllowedMentions(everyone=False), intents=discord.Intents(
                guild_messages=True, message_content=True, guilds=True,
            ),
            help_command=None,
            activity=discord.Game(name="Guild Bridge Bot")
        )
        self.mineflayer_bot = None
        self.redis_manager = None
        self.invite_queue: asyncio.Queue | None = None
        self._current_invite_future: asyncio.Future | None = None
        self._proc_inv_task: asyncio.Task | None = None

    async def send_invite(self, username):
        fut = asyncio.Future()
        self.invite_queue.put_nowait([username, fut])
        if self._proc_invite_task is None or self._proc_invite_task.done():
            self._proc_inv_task = asyncio.create_task(self._process_invites())
        return await fut

    async def on_ready(self):
        print(f"Discord > Bot Running as {self.user}")
        if self.mineflayer_bot is None:
            print("Discord > Starting the Minecraft bot...")
            self.mineflayer_bot = MinecraftBotManager.createbot(self)
        if self.redis_manager is None and redis_config.host:
            print("Discord > Starting the Redis manager...")
            self.redis_manager = await RedisManager.create(self, self.mineflayer_bot)
        if self._proc_inv_task is None or self._proc_inv_task.done():
            print("Discord > Starting the invite processor...")
            self._proc_inv_task = asyncio.create_task(self._process_invites())

    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            if str(message.content).startswith(discord_config.prefix):
                pass
            elif message.channel.id == int(discord_config.channel):
                self.mineflayer_bot.send_minecraft_message(message.author.display_name, message.content, "General")
            elif message.channel.id == int(discord_config.officerChannel):
                self.mineflayer_bot.send_minecraft_message(message.author.display_name, message.content, "Officer")
        await self.process_commands(message)

    async def on_command(self, ctx):
        print(f"Discord > Command {ctx.command} has been invoked by {ctx.author}")

    async def on_mc_bot_state_update(self, state):
        pass

    async def close(self):
        print(f"Discord > Bot {self.user} is shutting down...")
        if self.mineflayer_bot is not None:
            print("Discord > Stopping Minecraft bot...")
            self.mineflayer_bot.stop(False)
            print("Discord > Minecraft bot has been stopped.")
        if self.redis_manager is not None:
            print("Discord > Stopping redis...")
            await self.redis_manager.close()
            print("Discord > Redis has been stopped.")
        await super().close()

    async def _process_invites(self):
        if self.invite_queue is None:
            self.invite_queue = asyncio.Queue()
        try:
            while not self.is_closed():
                print("Discord > Waiting for invite...")
                username, fut = await self.invite_queue.get()
                print(f"Discord > Processing invite for {username}")
                self._current_invite_future = fut
                await self.mineflayer_bot.chat(f"/g invite {username}")
                try:
                    await asyncio.wait_for(fut, timeout=10)
                except asyncio.TimeoutError:
                    pass
                if not fut.done():
                    fut.set_result((False, "timeout"))
                self._current_invite_future = None
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Discord > Invite processor has been stopped: {e}")
            traceback.print_exc()
        print("Discord > Invite processor has been stopped.")

    # custom client events:
    # hypixel_guild_message
    # hypixel_guild_officer_message
    # hypixel_guild_invite_recieved
    # hypixel_guild_join_request
    # hypixel_guild_member_join
    # hypixel_guild_member_leave
    # hypixel_guild_member_promote
    # hypixel_guild_member_demote
    # hypixel_guild_member_kick
    # hypixel_guild_member_invite
    # hypixel_guild_member_invite_failed
    # hypixel_guild_message_send_failed
    async def send_discord_message(self, message):
        if "Unknown command" in message:
            self.dispatch("minecraft_pong")
        channel = self.get_channel(discord_config.channel)
        if message.startswith("Guild >"):
            if ":" not in message:
                if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                    if "]:" in message:
                        memberusername = message.split()[1]
                    else:
                        memberusername = message.split()[1][:-1]
                else:
                    if "]:" in message:
                        memberusername = message.split()[0]
                    else:
                        memberusername = message.split()[0][:-1]
                if self.mineflayer_bot.bot.username in memberusername:
                    return
                if " joined." in message:
                    embed = Embed(timestamp=discord.utils.utcnow(), colour=0x56F98A)
                    embed.set_author(name=message, icon_url="https://www.mc-heads.net/avatar/" + memberusername)
                else:
                    embed = Embed(timestamp=discord.utils.utcnow(), colour=0xFF6347)
                    embed.set_author(name=message, icon_url="https://www.mc-heads.net/avatar/" + memberusername)
            else:
                username, message = regex.match(message).groups()
                if self.mineflayer_bot.bot.username in username:
                    return
                if username.startswith("["):
                    username = username.split(" ")[1]
                else:
                    username = username.split(" ")[0]
                username = username.strip()

                embed = Embed(description=message, timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
                embed.set_author(name=username, icon_url="https://www.mc-heads.net/avatar/" + username)
                self.dispatch("hypixel_guild_message", username, message)

            try:
                if embed.author and embed.author.icon_url:
                    if not embed.author.icon_url.startswith("https://"):
                        raise ValueError("Invalid URL")
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Discord > Failed to send message {message} to channel {channel}: {e}")

        elif message.startswith("Officer >"):
            channel = self.get_channel(discord_config.officerChannel)
            if channel is None:
                return
            username, message = regex_officer.match(message).groups()
            if self.mineflayer_bot.bot.username in username:
                return
            message = message.replace("Guild >", "")
            if "[" in username:
                username = username.split("]")[1]
            username = username.strip()
            embed = Embed(description=message, timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(name=username, icon_url="https://www.mc-heads.net/avatar/" + username)
            self.dispatch("hypixel_guild_officer_message", username, message)
            await channel.send(embed=embed)

        # Bot recieved guild invite
        elif "Click here to accept or type /guild accept " in message:
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message.split()[2]
            else:
                playername = message.split()[1]

            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} invited me to a guild.",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )

            self.dispatch("hypixel_guild_invite_recieved", playername)

            await channel.send(embed=embed)

        # Someone joined/left the guild
        elif " joined the guild!" in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} has joined the guild!", icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            self.dispatch("hypixel_guild_member_join", playername)
            await channel.send(embed=embed)
        elif " left the guild!" in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} has left the guild!", icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_member_leave", playername)

        # Someone was promoted/demoted
        elif " was promoted from " in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            from_rank = message[-3]
            to_rank = message[-1]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} has been promoted from {from_rank} to {to_rank}!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_member_promote", playername, from_rank, to_rank)
        elif " was demoted from " in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            from_rank = message[-3]
            to_rank = message[-1]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} has been demoted from {from_rank} to {to_rank}!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)

            self.dispatch("hypixel_guild_member_demote", playername, from_rank, to_rank)

        # Someone was kicked
        elif " was kicked from the guild!" in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} was kicked from the guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_member_kick", playername)
        elif " was kicked from the guild by " in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} was kicked from the guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_member_kick", playername)

        # Join/leave notifications toggled
        elif "Disabled guild join/leave notifications!" in message:
            embed = Embed(description="Disabled guild join/leave notifications!", colour=0x1ABC9C)
            await channel.send(embed=embed)
        elif "Enabled guild join/leave notifications!" in message:
            embed = Embed(description="Enabled guild join/leave notifications!", colour=0x1ABC9C)
            await channel.send(embed=embed)

        # Hypixel antispam filter
        elif "You cannot say the same message twice!" in message:
            embed = Embed(description="You cannot say the same message twice!", colour=0x1ABC9C)
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_message_send_failed", message)

        # Bot cannot access officer chat
        elif "You don't have access to the officer chat!" in message:
            embed = Embed(description="You don't have access to the officer chat!", colour=0x1ABC9C)
            await channel.send(embed=embed)
            self.dispatch("hypixel_guild_message_send_failed", message)

        # Bot invited someone
        elif (
                ("You invited" in message and "to your guild. They have 5 minutes to accept." in message)
                or "You sent an offline invite to" in message
        ):
            message = message.split()
            if "You sent an offline invite to" in message:
                if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                    playername = message[7]
                else:
                    playername = message[6]
            else:
                if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                    playername = message[3]
                else:
                    playername = message[2]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} has been invited to the guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self._current_invite_future.set_result((True, None))
            self.dispatch("hypixel_guild_member_invite", playername)

        # Person bot invited is in another guild
        elif " is already in another guild!" in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} is already in another guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self._current_invite_future.set_result((False, 'inGuild'))
            self.dispatch("hypixel_guild_member_invite_failed", playername)

        # Person bot invited is in already in the guild
        elif " is already in your guild!" in message:
            message = message.split()
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} is already in your guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            await channel.send(embed=embed)
            self._current_invite_future.set_result((False, 'inThisGuild'))
            self.dispatch("hypixel_guild_member_invite_failed", playername)

        # Person bot invited has guild invites disabled (can't figure out who)
        elif "You cannot invite this player to your guild!" in message:
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"You cannot invite this player to your guild!",
            )
            await channel.send(embed=embed)
            self._current_invite_future.set_result((False, 'invitesOff'))
            self.dispatch("hypixel_guild_member_invite_failed", None)

        elif "Your guild is full!" in message:
            embed = Embed(colour=0x1ABC9C)
            embed.set_author(
                name=f"The guild is full!",
            )
            await channel.send(embed=embed)
            self._current_invite_future.set_result((False, 'guildFull'))
            self.dispatch("hypixel_guild_member_invite_failed", None)

        # /g list command response
        elif "Total Members:" in message:
            message = re.split("--", message)
            embed = ""
            length = len(message)
            for i in range(length):
                if i == 0:
                    pass
                elif i % 2 == 0:
                    ii = i - 1
                    embed += "**" + message[ii] + "** " + message[i]
            embed = Embed(description=embed.replace("_", "\\_"), colour=0x1ABC9C)
            await channel.send(embed=embed)

        # Everything else is sent as a normal message
        else:
            embed = Embed(description=message, colour=0x1ABC9C)
            await channel.send(embed=embed)
