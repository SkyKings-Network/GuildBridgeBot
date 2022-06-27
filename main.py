import re
import json
import discord
import os
import requests
import asyncio
from datetime import datetime
from discord.client import Client
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
from discord import Client, Intents, Embed



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

autoaccept = data["settings"]["autoaccept"]

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

async def main():
    async with client:
        await client.start(token)

@client.command()
async def help(ctx):
    embedVar = discord.Embed(title="Bridge Bot | Help Commands", description="``< >`` = Required arguments\n``[ ]`` = Optional arguments", colour=0x1ABC9C, timestamp=ctx.message.created_at)
    embedVar.add_field(name="Discord Commands", value=f"``{prefix}invite [username]``: Invites the user to the guild\n``{prefix}promote [username]``: Promotes the given user\n" +
    f"``{prefix}demote [username]``: Demotes the given user\n``{prefix}setrank [username] [rank]``: Sets the given user to a specific rank\n" +
    f"``{prefix}kick [username] <reason>``: Kicks the given user\n``{prefix}notifications``: Toggles join / leave notifications\n``{prefix}online``: Shows the online members\n" + 
    f"``{prefix}override <command>``: Forces the bot to use a given command\n``{prefix}toggleaccept``: Toggles auto accepting members joining the guild", inline=False)
    embedVar.add_field(name="Info", value=f"Prefix: ``{prefix}``\nGuild Channel: <#{channelid}>\nCommand Role: <@&{commandRole}>\nVersion: ``0.1``", inline=False)
    embedVar.set_footer(text=f"Made by SkyKings")
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
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        bot.chat("/" + command)
        embedVar = discord.Embed(description = f"``/{command}`` has been sent!", colour=0x1ABC9C)
        await ctx.send(embed=embedVar)
    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)

@client.command(aliases=['r'])
@has_permissions(manage_guild=True)  
async def relog(ctx, *, delay):
    try:
        delay = int(delay)
        role = ctx.guild.get_role(int(commandRole))
        if role in ctx.author.roles:
            embedVar = discord.Embed(description = "Relogging in " + str(delay) + " seconds")
            await ctx.send(embed=embedVar)
            await asyncio.sleep(delay)
            os.system("python main.py")
        else:
            embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
            await ctx.send(embed=embedVar)
    except KeyError:
        print("YO SOME SHIT HAS GONE HORRIBLY WRONG")

        

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
                type = "General"
                send_minecraft_message(discord, message.content, type)
        if message.channel.id == int(officerchannelid):
            if str(message.content).startswith(prefix):
                pass
            else:
                discord = message.author.name
                type = "Officer"
                send_minecraft_message(discord, message.content, type)
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

@client.command()
async def toggleaccept(ctx):
    role = ctx.guild.get_role(int(commandRole))
    if role in ctx.author.roles:
        autoaccept = data["settings"]["autoaccept"]
        if autoaccept == True:
            embedVar = discord.Embed(description = ":white_check_mark: Auto accepting guild invites is now ``off``!")
            await ctx.send(embed=embedVar)
            data["settings"]["autoaccept"] = False
            
        else:
            embedVar = discord.Embed(description = ":white_check_mark: Auto accepting guild invites is now ``on``!")
            await ctx.send(embed=embedVar)
            data["settings"]["autoaccept"] = True

        with open(filename, "w") as file:
            json.dump(data,file, indent=2)
        autoaccept = data["settings"]["autoaccept"]

    else:
        embedVar = discord.Embed(description = "<:x:930865879351189524> You do not have permission to use this command!")
        await ctx.send(embed=embedVar)


@On(bot, "login")
def login(this):
   print("Bot is logged in.")
   print(bot.username)
   global botusername
   botusername = bot.username

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
    print(message)
    global wait_response
    global messages
    
    if botusername == None:
        pass
    else:

        if message.startswith("Guild > " + botusername) or message.startswith("Officer > " + botusername):
            pass
        elif botusername in message and "Guild > " in message:
            pass
        elif botusername in message and "Officer > " in message:
            pass
        else:
            if message.startswith("Guild >"):
                messages = message
                send_discord_message(messages)

            if message.startswith("Officer >"):
                messages = message
                send_discord_message(messages)

            # Online Command
            if "Guild Name: " in message:
                messages = ""
                wait_response = True
            if wait_response is True:
                messages += "\n" + message
            if "Offline Members:" in message and wait_response:
                wait_response = False
                send_discord_message(messages)
                messages = ""

            if "Click here to accept or type /guild accept " in message:
                messages = message
                send_discord_message(messages)
                send_minecraft_message(None, messages, "invite")


            if " joined the guild!" in message:
                messages = message
                send_discord_message(messages)
            
            if " left the guild!" in message:
                messages = message
                send_discord_message(messages)

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
            if "You cannot say the same message twice!" in message:
                messages = message
                send_discord_message(messages)
            if "You don't have access to the officer chat!" in message:
                messages = message
                send_discord_message(messages)



def send_minecraft_message(discord, message, type):
    if type == "General":
        bot.chat("/gchat " + str(discord) + ": " + str(message))
    if type == "Officer":
        bot.chat("/ochat " + str(discord) + ": " + str(message))
    if type == "invite":
        autoaccept = data["settings"]["autoaccept"]
        if autoaccept == True:
            message = message.split()
            if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
                username = messages.split()[2]
            else:
                username = messages.split()[1]
            bot.chat(f"/guild accept {username}")


def send_minecraft_command(message):
    message = message.replace("!o ", "/")
    bot.chat(message)

def send_discord_message(messages):

    if messages.startswith("Guild >"):
        messages = messages.replace("Guild >", "")
        if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
            if "]:" in messages:
                memberusername = messages.split()[1]
            else:
                memberusername = messages.split()[1][:-1]
            
        else:
            if "]:" in messages:
                memberusername = messages.split()[0]
            else:
                memberusername = messages.split()[0][:-1]
            


        if " joined." in messages:
            embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x56F98A) 
            embedVar.set_author(name=messages, icon_url="https://www.mc-heads.net/avatar/" + memberusername)
        elif " left." in messages:
            embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0xFF6347) 
            embedVar.set_author(name=messages, icon_url="https://www.mc-heads.net/avatar/" + memberusername)

        else:
            messages = messages.split(":", maxsplit=1)
            messages = messages[1]

            embedVar = Embed(description=messages, timestamp=discord.utils.utcnow(), colour=0x1ABC9C) 
            embedVar.set_author(name=memberusername, icon_url="https://www.mc-heads.net/avatar/" + memberusername)

        requests.post(
        f"https://discord.com/api/v9/channels/{channelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )

    elif messages.startswith("Officer >"):
        messages = messages.replace("Officer >", "")
        if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
            if "]:" in messages:
                memberusername = messages.split()[1]
            else:
                memberusername = messages.split()[1][:-1]
            
        else:
            if "]:" in messages:
                memberusername = messages.split()[0]
            else:
                memberusername = messages.split()[0][:-1]
        
        messages = messages.split(":", maxsplit=1)
        messages = messages[1]

        embedVar = Embed(description=messages, timestamp=discord.utils.utcnow(), colour=0x1ABC9C) 
        embedVar.set_author(name=memberusername, icon_url="https://www.mc-heads.net/avatar/" + memberusername)


        requests.post(
        f"https://discord.com/api/v9/channels/{officerchannelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )


    elif "Click here to accept or type /guild accept " in messages:
        if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
            username = messages.split()[2]
        else:
            username = messages.split()[1]
        

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C) 
        embedVar.set_author(name=f"{username} has requested to join the guild.", icon_url="https://www.mc-heads.net/avatar/" + username)

        requests.post(
        f"https://discord.com/api/v9/channels/{channelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )

    elif " joined the guild!" in messages:
        messages = messages.split()
        if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
            username = messages[1]
        else:
            username = messages[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C) 
        embedVar.set_author(name=f"{username} has joined the guild!", icon_url="https://www.mc-heads.net/avatar/" + username)

        requests.post(
        f"https://discord.com/api/v9/channels/{channelid}/messages",
        headers={"Authorization": f"Bot {client.http.token}"},
        json={"embed": embedVar.to_dict() }
        )
    elif " left the guild!" in messages:
        messages = messages.split()
        if "[VIP]" in messages or "[VIP+]" in messages or "[MVP]" in messages or "[MVP+]" in messages or "[MVP++]" in messages:
            username = messages[1]
        else:
            username = messages[0]

        embedVar = Embed(timestamp=discord.utils.utcnow(), colour=0x1ABC9C) 
        embedVar.set_author(name=f"{username} has left the guild!", icon_url="https://www.mc-heads.net/avatar/" + username)

        requests.post(
        f"https://discord.com/api/v9/channels/{channelid}/messages",
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
                    embed += "**" + messages[ii] + "** " + messages[i] 

            embedVar = Embed(description=embed, colour=0x1ABC9C)
            requests.post(
            f"https://discord.com/api/v9/channels/{channelid}/messages",
            headers={"Authorization": f"Bot {client.http.token}"},
            json={"embed": embedVar.to_dict() }
            )
            messages = ""

        else:
            embedVar = Embed(description=messages, colour=0x1ABC9C)

            requests.post(
            f"https://discord.com/api/v9/channels/{channelid}/messages",
            headers={"Authorization": f"Bot {client.http.token}"},
            json={"embed": embedVar.to_dict() }
            )

asyncio.run(main())
