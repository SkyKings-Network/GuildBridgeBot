import requests
from discord.client import Client
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from discord import Client, Intents, Embed
import asyncio
import re
import json
import discord
import os

from javascript import require, On
mineflayer = require('mineflayer')

filename = "config.json"
global data
with open(filename, "r") as file:
    data = json.load(file)

host = data["server"]["host"]
port = data["server"]["port"]

username = data["minecraft"]["username"]
password = data["minecraft"]["password"]
accountType = data["minecraft"]["accountType"]

token = data["discord"]["token"]
channelid = data["discord"]["channel"]
officerchannelid = data["discord"]["officerChannel"]
commandRole = data["discord"]["commandRole"]
ownerID = data["discord"]["ownerId"]
prefix = data["discord"]["prefix"]

client = commands.Bot(command_prefix=commands.when_mentioned_or(prefix), case_insensitive=True,
                  allowed_mentions=discord.AllowedMentions(everyone=False), intents=discord.Intents.all(),
                  help_command=None)

bot = mineflayer.createBot({
    "host": host,
    "port": port,
    "username": username,
    "password": password,
    "version": "1.8.9",
    "auth": accountType
})

wait_response = False
messages = ""

@client.command()
async def help(ctx):
    embedVar = discord.Embed(title="Bridge Bot | Help Commands", description="For any extra support, DM JackTheGuy#0001", color=0xfbff00, timestamp=ctx.message.created_at)
    embedVar.add_field(name="!invite [username]", value="Invites a user to the guild.", inline=False)
    embedVar.add_field(name="!kick [username] [reason]", value="Kicks a user from the guild.", inline=False)
    embedVar.add_field(name="!promote [username]", value="Promotes the user in the guild.", inline=False)
    embedVar.add_field(name="!demote [username]", value="Demotes the user in the guild.", inline=False)
    embedVar.add_field(name="!setrank [username] [rank]", value="Sets the rank of the user to the selected rank.", inline=False)
    embedVar.add_field(name="!notifications", value="Enable/Disable join/leave notifications.", inline=False)
    embedVar.add_field(name="!online", value="Shows a list of online guild members.", inline=False)
    embedVar.set_thumbnail(url=ctx.author.avatar_url)       
    await ctx.send(embed=embedVar)


@client.event
async def on_ready():
    await client.wait_until_ready()
    await client.change_presence(activity=discord.Game(name="Guild Bridge Bot"))
    print(f"Bot Running as {client.user}")
    messages = "Bot Online"
    send_discord_message(messages)

@client.command()
async def online(ctx):
    bot.chat("/g online")

@client.command(aliases=['o', 'over'])
async def override(ctx, *, command):
    role = ctx.guild.get_role(int(ownerID))
    if role in ctx.author.roles:
        bot.chat("/" + command)
        embedVar = discord.Embed(description = "Command sent!")
        await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.check
async def on_command(ctx):
    print(ctx.command.qualified_name)
    return True

@client.event
async def on_message(message):
    if not message.author.bot:
        if message.channel.id == 929443410241290321:
            if str(message.content).startswith(prefix):
                pass
            else:
                discord = message.author.name
                send_minecraft_message(discord, message.content)
    await client.process_commands(message)

@client.command()
async def invite(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username == None:
            embedVar = discord.Embed(description = "Please enter a username!")
            await ctx.send(embed=embedVar)
        if username != None:
            bot.chat("/g invite " + username)
            embedVar = discord.Embed(description = username + " has been invited!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)
    

@client.command()
async def kick(ctx, username, reason):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username == None or reason == None:
            embedVar = discord.Embed(description = "Please enter a username and a reason!")
            await ctx.send(embed=embedVar)
        if username != None:
            bot.chat("/g kick " + username)
            embedVar = discord.Embed(description = username + " has been kicked for " + reason + "!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.command()
async def promote(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username == None:
            embedVar = discord.Embed(description = "Please enter a username!")
            await ctx.send(embed=embedVar)
        if username != None:
            bot.chat("/g promote " + username)
            embedVar = discord.Embed(description = username + " has been promoted!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.command()
async def setrank(ctx, username, rank):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username == None or rank == None:
            embedVar = discord.Embed(description = "Please enter a username and rank!")
            await ctx.send(embed=embedVar)
        if username != None:
            bot.chat("/g setrank " + username + " " + rank)
            embedVar = discord.Embed(description = username + " has been promoted to " + rank)
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.command()
async def demote(ctx, username):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        if username == None:
            embedVar = discord.Embed(description = "Please enter a username!")
            await ctx.send(embed=embedVar)
        if username != None:
            bot.chat("/g demote " + username)
            embedVar = discord.Embed(description = username + " has been demoted!")
            await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)
@client.command()
async def notifications(ctx):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        bot.chat("/g notifications")
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@On(bot, "login")
def login(this):
   print("Bot is logged in.")

   bot.chat("/§")

@On(bot, "end")
def kicked(this, reason):
    messages = "Bot Offline"
    send_discord_message(messages)
    print("Bot offline!")
    print(str(reason))
    print("Restarting...")
    os.system("python main.py")
    


@On(bot, "messagestr")
def chat(this, message, messagePosition, jsonMsg):
    global wait_response
    global messages
    print(message)
    if message.startswith("Guild > AirtightTooth43"):
        pass
    else:
        if message.startswith("Guild >"):
            messages = message
            send_discord_message(messages)

        if message.startswith("Officer >"):
            messages = message
            send_discord_message(messages)

        #For online command
        if " -- Guild Master --" in message:
            messages = ""
            wait_response = True
        if wait_response is True:
                messages += "\n" + message
        if "Offline Members:" in message and wait_response:
            wait_response = False
            send_discord_message(messages)
            messages = ""

        if " was promoted from " in message:
            messages = message
            send_discord_message(messages)
        if " was demoted from " in message:
            messages = message
            send_discord_message(messages)
        if " was kicked from the guild by " in message:
            messages = message
            send_discord_message(messages)
        if "Disabled guild join/leave notifications!" in message:
            messages = message
            send_discord_message(messages)
        if "Enabled guild join/leave notifications!" in message:
            messages = message
            send_discord_message(messages)



def send_minecraft_message(discord, message):
   print(message)
   bot.chat("/gchat " + str(discord) + ": " + str(message))

def send_minecraft_command(message):
    print(message)
    message = message.replace("!o ", "/")
    bot.chat(message)

def send_discord_message(messages):

    if messages.startswith("Guild >"):

        messages = messages.replace("Guild >", "")

        embedVar = Embed(description=messages)

        requests.post(
        f"https://discord.com/api/v9/channels/{channelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )
    elif messages.startswith("Officer >"):
        #messages = messages.replace("Officer >", "")

        embedVar = Embed(description=messages)

        requests.post(
        f"https://discord.com/api/v9/channels/{officerchannelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )

    else:
        if "Offline Members:" in messages:
            messages = re.split("--", messages)
            embed = ""
            length = len(messages)
            for i in range(length):
                if i == 0:
                    pass
                elif i % 2 == 0:
                    ii = i - 1
                    print(messages[ii] + messages[i])
                    embed += "\n**" + messages[ii] + "** " + messages[i] 

            embedVar = Embed(description=embed)
            print(embed)
            requests.post(
            f"https://discord.com/api/v9/channels/{channelid}/messages",
            headers={"Authorization": f"Bot {client.http.token}"},
            json={"embed": embedVar.to_dict() }
            )
            messages = ""

        else:
            embedVar = Embed(description=messages)

            requests.post(
            f"https://discord.com/api/v9/channels/{channelid}/messages",
            headers={"Authorization": f"Bot {client.http.token}"},
            json={"embed": embedVar.to_dict() }
            )

loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.create_task(client.start(token))
loop.run_forever()
