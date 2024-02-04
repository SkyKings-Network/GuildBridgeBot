import asyncio
import sys
import time

from javascript import require, On

from core.config import server, settings, account

mineflayer = require("mineflayer")


class MinecraftBotManager:
    def __init__(self, client, bot):
        self.client = client
        self.bot = bot
        self.wait_response = False
        self.message_buffer = []
        self.auto_restart = True
        self._online = False

    async def chat(self, message):
        await self.client.loop.run_in_executor(None, self.bot.chat, message)

    def stop(self, restart: bool = True):
        self.auto_restart = restart
        self.bot.quit()

    def send_to_discord(self, message):
        asyncio.run_coroutine_threadsafe(self.client.send_discord_message(message), self.client.loop)

    def oncommands(self):
        message_buffer = []

        @On(self.bot, "login")
        def login(this):
            print("Bot is logged in.")
            print(self.bot.username)
            self.bot.chat("§")
            if not self._online:
                self.send_to_discord("Bot Online")
            self._online = True

        @On(self.bot, "end")
        def kicked(this, reason):
            self._online = False
            print("Mineflayer > Bot offline!")
            self.send_to_discord("Bot Offline")
            if self.auto_restart:
                time.sleep(10)
                # maybe it changed between now and then
                if self.auto_restart:
                    print("Mineflayer > Restarting...")
                    new_bot = self.createbot(self.client)
                    self.client.mineflayer_bot = new_bot
            else:
                # kill this thread forcefully
                sys.exit(0)

        @On(self.bot, "error")
        def error(this, reason):
            print(reason)

        @On(self.bot, "messagestr")
        def chat(this, message, messagePosition, jsonMsg, sender, verified):
            def print_message(_message):
                max_length = 100  # Maximum length of each chunk
                chunks = [_message[i:i + max_length] for i in range(0, len(_message), max_length)]
                for chunk in chunks:
                    print(chunk)

            print_message(message)

            if self.bot.username is None:
                pass
            else:
                if message.startswith("Guild > " + self.bot.username) or message.startswith(
                        "Officer > " + self.bot.username
                        ):
                    pass
                else:
                    if message.startswith("Guild >") or message.startswith("Officer >"):
                        self.send_to_discord(message)

                    # Online Command
                    if message.startswith("Guild Name: "):
                        message_buffer.clear()
                        self.wait_response = True
                    if message == "-----------------------------------------------------":
                        self.wait_response = False
                        self.send_to_discord("\n".join(message_buffer))
                        message_buffer.clear()
                    if self.wait_response is True:
                        message_buffer.append(message)

                    if "Unknown command" in message:
                        self.send_to_discord(message)
                    if "Click here to accept or type /guild accept " in message:
                        self.send_to_discord(message)
                        self.send_minecraft_message(None, message, "invite")
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
                        self.send_to_discord(message)

    def send_minecraft_message(self, discord, message, type):
        if type == "General":
            message_text = f"/gchat {discord}: {message}"
            message_text = message_text[:256]
            self.bot.chat(message_text)
        if type == "Officer":
            message_text = f"/ochat {discord}: {message}"
            message_text = message_text[:256]
            self.bot.chat(message_text)

        if type == "invite":
            if settings.autoaccept:
                message = message.split()
                if ("[VIP]" in message or "[VIP+]" in message or
                        "[MVP]" in message or "[MVP+]" in message or "[MVP++]" in message):
                    username = message.split()[2]
                else:
                    username = message.split()[1]
                self.bot.chat(f"/guild accept {username}")

    def send_minecraft_command(self, message):
        message = message.replace("!o ", "/")
        self.bot.chat(message)

    @classmethod
    def createbot(cls, client):
        bot = mineflayer.createBot(
            {
                "host": server.host,
                "port": server.port,
                "version": "1.8.9",
                "username": account.email,
                "auth": "microsoft",
                "viewDistance": "tiny",
            }
        )
        botcls = cls(client, bot)
        client.mineflayer_bot = botcls
        botcls.oncommands()
        return botcls
