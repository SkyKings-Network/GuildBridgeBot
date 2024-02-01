import re
import json
import discord
import time
from typing import Any
import os
import asyncio
from datetime import datetime
from discord.client import Client
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from discord import Client, Intents, Embed
import subprocess
from redis_handler import RedisManager

import sys
from javascript import require, On

from redis_handler import RedisManager

mineflayer = require('mineflayer')

filename = "config.json"
global data
with open(filename, "r") as file:
    data = json.load(file)

host = data["server"]["host"]
port = data["server"]["port"]

accountusername = data["minecraft"]["username"]
accountType = data["minecraft"]["accountType"]

process_name = data["discord"]["process_name"]
token = data["discord"]["token"]
channelid = int(data["discord"]["channel"]) if data["discord"]["channel"] else None
officerchannelid = int(data["discord"]["officerChannel"]) if data["discord"]["officerChannel"] else None
commandRole = int(data["discord"]["commandRole"]) if data["discord"]["commandRole"] else None
overrideRole = int(data["discord"]["overrideRole"]) if data["discord"]["overrideRole"] else None
ownerID = int(data["discord"]["ownerId"]) if data["discord"]["ownerId"] else None
prefix = data["discord"]["prefix"]

autoaccept = data["settings"]["autoaccept"]

intents = Intents.default()
intents.message_content = True

client = commands.Bot(
    command_prefix=commands.when_mentioned_or(prefix), case_insensitive=True,
    allowed_mentions=discord.AllowedMentions(everyone=False), intents=intents,
    help_command=None
    )

bot: Any = None  # type: ignore

wait_response = False


async def main():
    async with client:
        redis_manager = RedisManager(client, bot, data["redis"])
        await redis_manager.start()
        client.redis_manager = redis_manager
        await client.start(token)


@client.command(name="help")
async def _help(ctx):
    embedVar = discord.Embed(
        title="Bridge Bot | Help Commands", description="``< >`` = Required arguments\n``[ ]`` = Optional arguments",
        colour=0x1ABC9C, timestamp=ctx.message.created_at
        )
    embedVar.add_field(
        name="Discord Commands",
        value=f"``{prefix}invite [username]``: Invites the user to the guild\n``{prefix}promote [username]``: Promotes the given user\n" +
              f"``{prefix}demote [username]``: Demotes the given user\n``{prefix}setrank [username] [rank]``: Sets the given user to a specific rank\n" +
              f"``{prefix}kick [username] <reason>``: Kicks the given user\n``{prefix}notifications``: Toggles join / leave notifications\n``{prefix}online``: Shows the online members\n" +
              f"``{prefix}override <command>``: Forces the bot to use a given command\n``{prefix}toggleaccept``: Toggles auto accepting members joining the guild\n" +
              f"``{prefix}mute (username) (time)`` - Mutes the user for a specific time\n``{prefix}unmute (username)`` - Unmutes the user",
        inline=False
        )
    embedVar.add_field(
        name="Info",
        value=f"Prefix: ``{prefix}``\nGuild Channel: <#{channelid}>\nCommand Role: <@&{commandRole}>\nOverride Role: <@&{overrideRole}>\nVersion: ``0.2``",
        inline=False
        )
    embedVar.set_footer(text=f"Made by SkyKings")
    await ctx.send(embed=embedVar)


@client.event
async def on_ready():
    await client.wait_until_ready()
    await client.change_presence(activity=discord.Game(name="Guild Bridge Bot"))
    print(f"Bot Running as {client.user}")
    createbot()


@client.command()
async def online(ctx):
    bot.chat("/g online")


@client.command(name="list")
async def _list(ctx):
    bot.chat("/g list")


@client.command(aliases=['o', 'over'])
async def override(ctx, *, command):
    role = ctx.guild.get_role(int(commandRole))
    role2 = ctx.guild.get_role(int(overrideRole))
    if role in ctx.author.roles and role2 in ctx.author.roles:
        bot.chat("/" + command)
        embedVar = discord.Embed(description=f"``/{command}`` has been sent!", colour=0x1ABC9C)
        await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command(aliases=['r'])
async def relog(ctx, *, delay):
    try:
        delay = int(delay)
        role = ctx.guild.get_role(int(commandRole))
        if role in ctx.author.roles:
            embedVar = discord.Embed(description="Relogging in " + str(delay) + " seconds")
            await ctx.send(embed=embedVar)
            await asyncio.sleep(delay)
            os.system(f"pm2 restart {process_name}")
        else:
            embedVar = discord.Embed(
                description="<:x:930865879351189524> You do not have permission to use this command!"
                )
            await ctx.send(embed=embedVar)
    except KeyError:
        print("Error")


@client.check
async def on_command(ctx):
    print(ctx.command.qualified_name)
    return True


@client.event
async def on_message(message):
    if not message.author.bot:
        if message.channel.id == int(channelid):
            if str(message.content).startswith(prefix):
                pass
            else:
                discord = message.author.name
                send_minecraft_message(discord, message.content, "General")
        if message.channel.id == int(officerchannelid):
            if str(message.content).startswith(prefix):
                pass
            else:
                discord = message.author.name
                send_minecraft_message(discord, message.content, "Officer")
    try:
        await client.process_commands(message)
    except Exception as e:
        print(e)

@client.command()
async def update(ctx):
    role = ctx.guild.get_role(int(overrideRole))
    if role in ctx.author.roles:
        embedVar = discord.Embed(description=":white_check_mark: Rebooting Bot...")
        await ctx.send(embed=embedVar)
        os.system("git pull")
        await asyncio.sleep(10)
        print("Rebooting Bot (/update)")
        os.system(f"pm2 restart {process_name}")


    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.command()
async def invite(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None:
            embedVar = discord.Embed(description="Please enter a username!")
            await ctx.send(embed=embedVar)
        if username is not None:
            bot.chat("/g invite " + username)
            embedVar = discord.Embed(description=username + " has been invited!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def kick(ctx, username, reason):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None or reason is None:
            embedVar = discord.Embed(description="Please enter a username and a reason!")
            await ctx.send(embed=embedVar)
        if username is not None:
            bot.chat("/g kick " + username)
            embedVar = discord.Embed(description=username + " has been kicked for " + reason + "!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def promote(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None:
            embedVar = discord.Embed(description="Please enter a username!")
            await ctx.send(embed=embedVar)
        if username is not None:
            bot.chat("/g promote " + username)
            embedVar = discord.Embed(description=username + " has been promoted!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def mute(ctx, username, time):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None or time is None:
            embedVar = discord.Embed(description="Please enter a username and time! ``!mute (username) (time)")
            await ctx.send(embed=embedVar)
        else:
            bot.chat("/g mute " + username + " " + time)
            embedVar = discord.Embed(description=username + " has been muted for " + time)
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def unmute(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None or time is None:
            embedVar = discord.Embed(description="Please enter a username! ``!unmute (username)")
            await ctx.send(embed=embedVar)
        else:
            bot.chat("/g unmute " + username)
            embedVar = discord.Embed(description=username + " has been unmuted")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def setrank(ctx, username, rank):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None or rank is None:
            embedVar = discord.Embed(description="Please enter a username and rank!")
            await ctx.send(embed=embedVar)
        if username is not None:
            bot.chat("/g setrank " + username + " " + rank)
            embedVar = discord.Embed(description=username + " has been promoted to " + rank)
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def demote(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username is None:
            embedVar = discord.Embed(description="Please enter a username!")
            await ctx.send(embed=embedVar)
        if username is not None:
            bot.chat("/g demote " + username)
            embedVar = discord.Embed(description=username + " has been demoted!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def notifications(ctx):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        bot.chat("/g notifications")
    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@client.command()
async def toggleaccept(ctx):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if autoaccept:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``off``!")
            await ctx.send(embed=embedVar)
            data["settings"]["autoaccept"] = False

        else:
            embedVar = discord.Embed(description=":white_check_mark: Auto accepting guild invites is now ``on``!")
            await ctx.send(embed=embedVar)
            data["settings"]["autoaccept"] = True

        with open(filename, "w") as file:
            json.dump(data, file, indent=2)

    else:
        embedVar = discord.Embed(description="<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


# custom client events:
# hypixel_guild_message
# hypixel_guild_officer_message
# hypixel_guild_join_request
# hypixel_guild_member_join
# hypixel_guild_member_leave
# hypixel_guild_member_promote
# hypixel_guild_member_demote
# hypixel_guild_member_kick
# hypixel_guild_member_invite
# hypixel_guild_member_invite_failed
# hypixel_guild_message_send_failed

# to send discord messages, dispatch send_discord_message w/ message contents

@client.event
async def on_send_discord_message(message):
    channel = client.get_channel(channelid)
    if message.startswith("Guild >"):
        message = message.replace("Guild >", "")
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

        if " joined." in message:
            embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x56F98A)
            embedVar.set_author(name=message, icon_url="https://www.mc-heads.net/avatar/" + memberusername)
        elif " left." in message:
            embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0xFF6347)
            embedVar.set_author(name=message, icon_url="https://www.mc-heads.net/avatar/" + memberusername)
        else:
            message = message.split(":", maxsplit=1)
            message = message[1]

            embedVar = Embed(description=message, timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
            embedVar.set_author(name=memberusername, icon_url="https://www.mc-heads.net/avatar/" + memberusername)

            client.dispatch("hypixel_guild_message", memberusername, message)

        await channel.send(embed=embedVar)

    elif message.startswith("Officer >"):
        message = message.replace("Officer >", "")
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
        message = message.split(":", maxsplit=1)
        message = message[1]

        embedVar = Embed(description=message, timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(name=memberusername, icon_url="https://www.mc-heads.net/avatar/" + memberusername)

        client.dispatch("hypixel_guild_officer_message", memberusername, message)

        await channel.send(embed=embedVar)

    elif "Click here to accept or type /guild accept " in message:
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message.split()[2]
        else:
            playername = message.split()[1]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has requested to join the guild.",
            icon_url="https://www.mc-heads.net/avatar/" + playername
            )

        client.dispatch("hypixel_guild_join_request", playername)

        await channel.send(embed=embedVar)

    elif " joined the guild!" in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has joined the guild!", icon_url="https://www.mc-heads.net/avatar/" + playername
            )

        client.dispatch("hypixel_guild_member_join", playername)

        await channel.send(embed=embedVar)

    elif " left the guild!" in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has left the guild!", icon_url="https://www.mc-heads.net/avatar/" + playername
            )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_leave", playername)

    elif " was promoted from " in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        from_rank = message[-3]
        to_rank = message[-1]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has been promoted from {from_rank} to {to_rank}!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_promote", playername, from_rank, to_rank)

    elif " was demoted from " in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        from_rank = message[-3]
        to_rank = message[-1]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has been demoted from {from_rank} to {to_rank}!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_demote", playername, from_rank, to_rank)

    elif " was kicked from the guild!" in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} was kicked from the guild!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_kick", playername)

    elif " was kicked from the guild by " in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} was kicked from the guild!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_kick", playername)

    elif "Disabled guild join/leave notifications!" in message:
        embedVar = Embed(description="Disabled guild join/leave notifications!", colour=0x1ABC9C)
        await channel.send(embed=embedVar)

    elif "Enabled guild join/leave notifications!" in message:
        embedVar = Embed(description="Enabled guild join/leave notifications!", colour=0x1ABC9C)
        await channel.send(embed=embedVar)

    elif "You cannot say the same message twice!" in message:
        embedVar = Embed(description="You cannot say the same message twice!", colour=0x1ABC9C)
        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_message_send_failed", message)

    elif "You don't have access to the officer chat!" in message:
        embedVar = Embed(description="You don't have access to the officer chat!", colour=0x1ABC9C)
        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_message_send_failed", message)

    elif ("You invited" in message and "to your guild. They have 5 minutes to accept." in message) or "You sent an offline invite to" in message:
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

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} has been invited to the guild!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_invite", playername)

    elif " is already in another guild!" in message:
        message = message.split()
        if "[VIP]" in message or "[VIP+]" in message or "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message:
            playername = message[1]
        else:
            playername = message[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"{playername} is already in another guild!",
            icon_url="https://www.mc-heads.net/avatar/" + playername
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_invite_failed", playername)

    elif "You cannot invite this player to your guild!" in message:
        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C)
        embedVar.set_author(
            name=f"You cannot invite this player to your guild!",
        )

        await channel.send(embed=embedVar)

        client.dispatch("hypixel_guild_member_invite_failed", None)

    else:
        if "Offline Members:" in message:
            message = re.split("--", message)
            embed = ""
            length = len(message)
            for i in range(length):
                if i == 0:
                    pass
                elif i % 2 == 0:
                    ii = i - 1
                    embed += "**" + message[ii] + "** " + message[i]

            embedVar = Embed(description=embed, colour=0x1ABC9C)
            await channel.send(embed=embedVar)

        else:
            embedVar = Embed(description=message, colour=0x1ABC9C)

            await channel.send(embed=embedVar)


def oncommands():
    message_buffer = []

    @On(bot, "login")
    def login(this):
        client.dispatch("send_discord_message", "Bot Online")
        print("Bot is logged in.")
        print(bot.username)

        bot.chat("/§")

    @On(bot, "end")
    def kicked(this, reason):
        client.dispatch("send_discord_message", "Bot Offline")
        time.sleep(30)
        print("Bot offline!")
        sys.exit()
        
        # print(str(reason))
        # print("Restarting...")
        # createbot()

    @On(bot, "error")
    def error(this, reason):
        print(reason)

    @On(bot, "messagestr")
    def chat(this, message, messagePosition, jsonMsg, sender, verified):
        def print_message(_message):
            max_length = 100  # Maximum length of each chunk
            chunks = [_message[i:i + max_length] for i in range(0, len(_message), max_length)]
            for chunk in chunks:
                print(chunk)

        print_message(message)

        global wait_response

        if bot.username is None:
            pass
        else:
            if message.startswith("Guild > " + bot.username) or message.startswith("Officer > " + bot.username):
                pass
            elif bot.username in message and "Guild > " in message:
                pass
            elif bot.username in message and "Officer > " in message:
                pass
            else:
                if message.startswith("Guild >"):
                    client.dispatch("send_discord_message", message)

                elif message.startswith("Officer >"):
                    client.dispatch("send_discord_message", message)

                # Online Command
                elif "Guild Name: " in message:
                    message_buffer.clear()
                    wait_response = True
                if wait_response is True:
                    message_buffer.append(message)
                if "Offline Members:" in message and wait_response:
                    wait_response = False
                    client.dispatch("send_discord_message", "\n".join(message_buffer))
                    message_buffer.clear()
                if "Unknown command" in message:
                    client.dispatch("minecraft_pong", message)
                if "Click here to accept or type /guild accept " in message:
                    client.dispatch("send_discord_message", message)
                    send_minecraft_message(None, message, "invite")
                elif " is already in another guild!" in message or \
                        ("You invited" in message and "to your guild. They have 5 minutes to accept." in message) or \
                        " joined the guild!" in message or \
                        " left the guild!" in message or \
                        " was promoted from " in message or \
                        " was demoted from " in message or \
                        " was kicked from the guild!" in message or \
                        " was kicked from the guild by " in message or \
                        "You cannot invite this player to your guild!" in message or \
                        "Disabled guild join/leave notifications!" in message or \
                        "Enabled guild join/leave notifications!" in message or \
                        "You cannot say the same message twice!" in message or \
                        "You don't have access to the officer chat!" in message:
                    client.dispatch("send_discord_message", message)


def send_minecraft_message(discord, message, type):
    if type == "General":
        bot.chat("/gchat " + str(discord) + ": " + str(message))
    if type == "Officer":
        bot.chat("/ochat " + str(discord) + ": " + str(message))
    if type == "invite":
        if autoaccept:
            message = message.split()
            if ("[VIP]" in message or "[VIP+]" in message or
                    "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message):
                username = message.split()[2]
            else:
                username = message.split()[1]
            bot.chat(f"/guild accept {username}")


def send_minecraft_command(message):
    message = message.replace("!o ", "/")
    bot.chat(message)


def createbot():
    global bot
    bot = mineflayer.createBot(
        {
            "host": host,
            "port": port,
            "username": accountusername,
            "version": "1.8.9",
            "auth": accountType,
            "viewDistance": "tiny",
            "version": "1.8.9"
        }
    )
    client.redis_manager.mineflayer_bot = bot
    oncommands()
    
asyncio.run(main())