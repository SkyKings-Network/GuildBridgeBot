import asyncio
import sys
import time
import logging
import os
import traceback

import javascript
from javascript import require, On, config

from core.colors import Color
from core.config import ServerConfig, SettingsConfig, AccountConfig


class MinecraftBotManager:
    def __init__(self, client, bot):
        self.client = client
        self.bot = bot
        self.wait_response = False
        self.message_buffer = []
        self.auto_restart = True
        self._online = False
        self._starting = False
        if SettingsConfig.printChat:
            print(f"{Color.GREEN}Minecraft{Color.RESET} > {Color.YELLOW}[WARNING]{Color.RESET} Chat logging is enabled!")

    def is_ready(self):
        return self._online and not self._starting

    def is_online(self):
        return self._online

    def is_starting(self):
        return self._starting

    async def chat(self, message):
        await self.client.loop.run_in_executor(None, self.bot.chat, message)

    def stop(self, restart: bool = True):
        print(f"{Color.GREEN}Minecraft{Color.RESET} > Stopping bot...")
        # idk why but this literally never works
        # so skip it and force terminate the js environment
        # try:
        #     self.bot.quit()
        # except Exception as e:
        #     pass
        self._starting = restart
        self._online = False
        javascript.terminate()
        if restart:
            time.sleep(3)
            print(f"{Color.GREEN}Minecraft{Color.RESET} > Restarting...")
            try:
                self.createbot(self.client)
            except Exception as e:
                print(f"{Color.GREEN}Minecraft{Color.RESET} > Error: {e}")
                traceback.print_exc()
                raise


    def send_to_discord(self, message):
        if SettingsConfig.printChat:
            print(f"{Color.GREEN}Minecraft{Color.RESET} > Dispatching to Discord")
        asyncio.run_coroutine_threadsafe(self.client.send_discord_message(message), self.client.loop)

    def oncommands(self):
        message_buffer = []

        @javascript.On(self.bot, "spawn")
        def login(this):
            if not self._online:
                self.send_to_discord("Bot Online")
                print(f"{Color.GREEN}Minecraft{Color.RESET} > Bot is logged in as", self.bot.username)
            self._online = True
            self.client.dispatch("minecraft_ready")

        @javascript.On(self.bot, "end")
        def end(this, reason):
            print(f"{Color.GREEN}Minecraft{Color.RESET} > Bot offline: {reason}")
            self.send_to_discord("Bot Offline")
            self.client.dispatch("minecraft_disconnected")
            self.stop(self.auto_restart)

        @javascript.On(self.bot, "kicked")
        def kicked(this, reason, loggedIn):
            print(f"{Color.GREEN}Minecraft{Color.RESET} > Bot kicked: {reason}")
            self.client.dispatch("minecraft_disconnected")
            if loggedIn:
                self.send_to_discord(f"Bot kicked: {reason}")
                self.stop(True)
            else:
                self.send_to_discord(f"Bot kicked before logging in: {reason}")
                self.stop(False)

        @javascript.On(self.bot, "error")
        def error(this, reason):
            print(reason)
            self.client.dispatch("minecraft_error")

        @javascript.On(self.bot, "messagestr")
        def chat(this, message, *args):
            if self.bot.username is None:
                pass
            else:
                if SettingsConfig.printChat:
                    print(f"{Color.GREEN}Minecraft{Color.RESET} > Chat: {message}")
                if message.startswith("Guild > " + self.bot.username) or message.startswith(
                        "Officer > " + self.bot.username
                ):
                    pass
                else:
                    if message.startswith("Guild >") or message.startswith("Officer >"):
                        self.send_to_discord(message)

                    # Online Command / GEXP Command
                    if (
                            message.startswith("Guild Name: ") or
                            "Top Guild Experience" in message or
                            message.startswith("Created: ")
                    ):
                        message_buffer.clear()
                        self.wait_response = True
                        if SettingsConfig.printChat:
                            print(f"{Color.GREEN}Minecraft{Color.RESET} > Buffering chat...")
                    if message == "-----------------------------------------------------" and self.wait_response:
                        self.wait_response = False
                        self.send_to_discord("\n".join(message_buffer))
                        message_buffer.clear()
                        if SettingsConfig.printChat:
                            print(f"{Color.GREEN}Minecraft{Color.RESET} > End of chat buffer")
                    if self.wait_response is True:
                        message_buffer.append(message)
                        return

                    if "Unknown command" in message:
                        self.send_to_discord(message)
                    if "Click here to accept or type /guild accept " in message:
                        self.send_to_discord(message)
                    elif " is already in another guild!" in message or \
                            ("You invited" in message and "to your guild. They have 5 minutes to accept." in message) or \
                            "You sent an offline invite to " in message or \
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
                            "You don't have access to the officer chat!" in message or \
                            "Your guild is full!" in message or \
                            "is already in your guild!" in message or \
                            ("has muted" in message and "for" in message) or \
                            "has unmuted" in message or \
                            "You're currently guild muted" in message or \
                            "Guild Log" in message or \
                            ("You've already invited" in message and "to your guild! Wait for them to accept!" in message) or \
                            " has requested to join the guild!" in message.lower():
                        # Guild log is sent as one fat message
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

    def send_minecraft_command(self, message):
        message = message.replace("!o ", "/")
        self.bot.chat(message)

    @classmethod
    def createbot(cls, client):
        javascript.init()
        mineflayer = javascript.require("mineflayer")
        print(f"{Color.GREEN}Minecraft{Color.RESET} > Creating the bot...")
        bot = mineflayer.createBot(
            {
                "host": ServerConfig.host,
                "port": ServerConfig.port,
                "version": "1.8.9",
                "username": AccountConfig.email,
                "auth": "microsoft",
                "viewDistance": "tiny",
            }
        )
        print(f"{Color.GREEN}Minecraft{Color.RESET} > Initialized")
        botcls = cls(client, bot)
        client.mineflayer_bot = botcls
        botcls._starting = True
        try:
            botcls.oncommands()
        except Exception as e:
            if "Call to 'on' timed out" in str(e):
                print(f"{Color.GREEN}Minecraft{Color.RESET} > Error: {e}")
                print(f"{Color.GREEN}Minecraft{Color.RESET} > Restarting...")
                botcls.stop()
                return cls.createbot(client)
            raise
        print(f"{Color.GREEN}Minecraft{Color.RESET} > Events registered")
        botcls._starting = False
        return botcls
