import asyncio
import os
import re
import threading
import traceback
from typing import Union

import aiohttp
import discord
from discord import Embed
from discord.ext import commands

from core.config import discord as discord_config, redis as redis_config
from core.minecraft_bot import MinecraftBotManager
from core.redis_handler import RedisManager

regex = re.compile(r"Guild > ([\[\]+ a-zA-Z0-9_]+): (.+)")
regex_officer = re.compile(r"Officer > ([\[\]+ a-zA-Z0-9_]+): (.+)")

emoji_regex = re.compile(r"<a?:(\w+):\d+>")
mention_regex = re.compile(r"<@!?(\d+)>")
role_mention_regex = re.compile(r"<@&(\d+)>")
channel_mention_regex = re.compile(r"<#(\d+)>")
slash_mention_regex = re.compile(r"</([\w\- ]+):\d+>")


def emoji_repl(match):
    return f":{match.group(1)}:"


def slash_mention_repl(match):
    return f"/{match.group(1)}"


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
        self.webhook: discord.Webhook | None = None
        self.officer_webhook: discord.Webhook | None = None

    async def send_invite(self, username):
        fut = asyncio.Future()
        self.invite_queue.put_nowait([username, fut])
        if self._proc_inv_task is None or self._proc_inv_task.done():
            self._proc_inv_task = asyncio.create_task(self._process_invites())
        return await fut

    def init_webhooks(self):
        if discord_config.webhookURL:
            self.webhook = discord.Webhook.from_url(discord_config.webhookURL, client=self)
        if discord_config.officerWebhookURL:
            self.officer_webhook = discord.Webhook.from_url(discord_config.officerWebhookURL, client=self)

    async def on_ready(self):
        print(f"Discord > Bot Running as {self.user}")
        channel = self.get_channel(discord_config.channel)
        if channel is None:
            print(f"Discord > Channel {discord_config.channel} not found! Please set the correct channel ID!")
            await self.close()
        self.init_webhooks()
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
                await self.send_minecraft_user_message(message.author.display_name, message)
            elif message.channel.id == int(discord_config.officerChannel):
                await self.send_minecraft_user_message(message.author.display_name, message, officer=True)
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

    async def _send_message(self, *args, **kwargs) -> Union[discord.Message, discord.WebhookMessage, None]:
        kwargs["allowed_mentions"] = discord.AllowedMentions.none()
        if kwargs.pop("officer", False):
            if self.officer_webhook:
                kwargs["wait"] = True
                try:
                    return await self.officer_webhook.send(*args, **kwargs)
                except Exception as e:
                    print(f"Discord > Failed to send message to officer webhook: {e}")
            else:
                channel = self.get_channel(discord_config.officerChannel)
                if channel is None:
                    return
                try:
                    return await channel.send(*args, **kwargs)
                except Exception as e:
                    print(f"Discord > Failed to send message to officer channel {channel}: {e}")
        else:
            if self.webhook:
                kwargs["wait"] = True
                try:
                    return await self.webhook.send(*args, **kwargs)
                except Exception as e:
                    print(f"Discord > Failed to send message to webhook: {e}")
            else:
                channel = self.get_channel(discord_config.channel)
                if channel is None:
                    print(f"Discord > Channel {discord_config.channel} not found! Please set the correct channel ID!")
                    return
                try:
                    return await channel.send(*args, **kwargs)
                except Exception as e:
                    print(f"Discord > Failed to send message to channel {channel}: {e}")

    async def send_message(self, *args, **kwargs) -> Union[discord.Message, discord.WebhookMessage, None]:
        retry = kwargs.pop("retry", True)
        try:
            return await self._send_message(*args, **kwargs)
        except aiohttp.ClientError as e:
            if retry:
                self.init_webhooks()
                return await self.send_message(*args, **kwargs, retry=False)

    async def send_user_message(
        self, username, message, *, officer: bool = False
    ) -> Union[discord.Message, discord.WebhookMessage, None]:
        if self.webhook:
            return await self.send_message(
                username=username,
                avatar_url="https://www.mc-heads.net/avatar/" + username,
                content=message,
                officer=officer,
            )
        else:
            embed = Embed(description=message, colour=0x1ABC9C, timestamp=discord.utils.utcnow())
            embed.set_author(name=username, icon_url="https://www.mc-heads.net/avatar/" + username)
            return await self.send_message(embed=embed, officer=officer)

    async def send_minecraft_user_message(self, username, message: discord.Message, *, officer: bool = False):
        content = message.content
        # replace emojis
        content = emoji_regex.sub(emoji_repl, content)
        # replace member mentions
        mentions = message.mentions
        for mention in mentions:
            content = content.replace(f"<@!{mention.id}>", f"@{mention.name}")
            content = content.replace(f"<@{mention.id}>", f"@{mention.name}")
        # replace role mentions
        roles = message.role_mentions
        for role in roles:
            content = content.replace(f"<@&{role.id}>", f"@{role.name}")
        # channel mentions
        channels = message.channel_mentions
        for channel in channels:
            content = content.replace(f"<#{channel.id}>", f"#{channel.name}")
        # slash mentions
        content = slash_mention_regex.sub(slash_mention_repl, content)
        # replace the rest of the mentions
        user_mentions = set(mention_regex.findall(content))
        for mention in user_mentions:
            userid = int(mention)
            try:
                user = await self.fetch_user(int(mention))
                content = content.replace(f"<@!{mention}>", f"@{user.name}")
                content = content.replace(f"<@{mention}>", f"@{user.name}")
            except discord.NotFound:
                content = content.replace(f"<@&{mention}>", f"@unknown-user")
        role_mentions = set(role_mention_regex.findall(content))
        for mention in role_mentions:
            roleid = int(mention)
            role = message.guild.get_role(roleid)
            if role:
                content = content.replace(f"<@&{mention}>", f"@{role.name}")
            else:
                content = content.replace(f"<@&{mention}>", f"@unknown-role")
        channel_mentions = set(channel_mention_regex.findall(content))
        for mention in channel_mentions:
            channelid = int(mention)
            channel = self.get_channel(channelid)
            if channel:
                content = content.replace(f"<#{mention}>", f"#{channel.name}")
            else:
                content = content.replace(f"<#{mention}>", f"#unknown-channel")
        if content.strip() == "":
            try:
                await message.add_reaction("❌")
            except discord.HTTPException:
                pass
            return
        if officer:
            content = f"/oc {username}: {content}"
        else:
            content = f"/gc {username}: {content}"
        if len(content) > 256:
            content = content[:253] + "..."
        await self.mineflayer_bot.chat(content)

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
                await self.send_message(embed=embed)
            else:
                username, message = regex.match(message).groups()
                if self.mineflayer_bot.bot.username in username:
                    return
                if username.startswith("["):
                    username = username.split(" ")[1]
                else:
                    username = username.split(" ")[0]
                username = username.strip()

                self.dispatch("hypixel_guild_message", username, message)
                await self.send_user_message(username, message)

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
            self.dispatch("hypixel_guild_officer_message", username, message)
            await self.send_user_message(username, message, officer=True)

        # Bot recieved guild invite
        elif "Click here to accept or type /guild accept " in message:
            if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
                playername = message.split()[2]
            else:
                playername = message.split()[1]

            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} invited me to a guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )

            self.dispatch("hypixel_guild_invite_recieved", playername)
            await self.send_message(embed=embed)

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
            await self.send_message(embed=embed)
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
            self.dispatch("hypixel_guild_member_leave", playername)
            await self.send_message(embed=embed)

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
            self.dispatch("hypixel_guild_member_promote", playername, from_rank, to_rank)
            await self.send_message(embed=embed)
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
            self.dispatch("hypixel_guild_member_demote", playername, from_rank, to_rank)
            await self.send_message(embed=embed)

        # Someone was kicked
        elif " was kicked from the guild!" in message:
            message = message.split()
            if "[VIP]" in message[0] or "[VIP+]" in message[0] or "[MVP]" in message[0] or "[MVP+]" in message[0] or "[MVP++]" in message[0]:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} was kicked from the guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            self.dispatch("hypixel_guild_member_kick", playername)
            await self.send_message(embed=embed)
        elif " was kicked from the guild by " in message:
            message = message.split()
            if "[VIP]" in message[0] or "[VIP+]" in message[0] or "[MVP]" in message[0] or "[MVP+]" in message[0] or "[MVP++]" in message[0]:
                playername = message[1]
            else:
                playername = message[0]
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"{playername} was kicked from the guild!",
                icon_url="https://www.mc-heads.net/avatar/" + playername
            )
            self.dispatch("hypixel_guild_member_kick", playername)
            await self.send_message(embed=embed)

        # Join/leave notifications toggled
        elif "Disabled guild join/leave notifications!" in message:
            embed = Embed(description="Disabled guild join/leave notifications!", colour=0x1ABC9C)
            await self.send_message(embed=embed)
        elif "Enabled guild join/leave notifications!" in message:
            embed = Embed(description="Enabled guild join/leave notifications!", colour=0x1ABC9C)
            await self.send_message(embed=embed)

        # Hypixel antispam filter
        elif "You cannot say the same message twice!" in message:
            embed = Embed(description="You cannot say the same message twice!", colour=0x1ABC9C)
            self.dispatch("hypixel_guild_message_send_failed", message)
            await self.send_message(embed=embed)

        # Bot cannot access officer chat
        elif "You don't have access to the officer chat!" in message:
            embed = Embed(description="You don't have access to the officer chat!", colour=0x1ABC9C)
            self.dispatch("hypixel_guild_message_send_failed", message)
            await self.send_message(embed=embed)

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
            self._current_invite_future.set_result((True, None))
            self.dispatch("hypixel_guild_member_invite", playername)
            await self.send_message(embed=embed)

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
            self._current_invite_future.set_result((False, 'inGuild'))
            self.dispatch("hypixel_guild_member_invite_failed", playername)
            await self.send_message(embed=embed)

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
            self._current_invite_future.set_result((False, 'inThisGuild'))
            self.dispatch("hypixel_guild_member_invite_failed", playername)
            await self.send_message(embed=embed)

        # Person bot invited has guild invites disabled (can't figure out who)
        elif "You cannot invite this player to your guild!" in message:
            embed = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embed.set_author(
                name=f"You cannot invite this player to your guild!",
            )
            self._current_invite_future.set_result((False, 'invitesOff'))
            self.dispatch("hypixel_guild_member_invite_failed", None)
            await self.send_message(embed=embed)

        elif "Your guild is full!" in message:
            embed = Embed(colour=0x1ABC9C)
            embed.set_author(
                name=f"The guild is full!",
            )
            self._current_invite_future.set_result((False, 'guildFull'))
            self.dispatch("hypixel_guild_member_invite_failed", None)
            await self.send_message(embed=embed)

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
            await self.send_message(embed=embed)

        # Everything else is sent as a normal message
        else:
            embed = Embed(colour=0x1ABC9C).set_author(name=message)
            await self.send_message(embed=embed)
