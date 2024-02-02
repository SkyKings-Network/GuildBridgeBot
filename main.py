from core.discord_bot import DiscordBridgeBot
import asyncio
from core.config import discord as config

bot = DiscordBridgeBot()


async def main():
    async with bot:
        await bot.load_extension("discord_extensions.admin")
        await bot.load_extension("discord_extensions.bridge")
        await bot.load_extension("discord_extensions.generic")
        await bot.start(config.token)


asyncio.run(main())
