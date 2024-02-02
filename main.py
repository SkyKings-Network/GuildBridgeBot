from core.discord_bot import DiscordBridgeBot
import asyncio
from core.config import discord as config

bot = DiscordBridgeBot()


async def main():
    async with bot:
        await bot.load_extension("commands.admin")
        await bot.load_extension("commands.bridge")
        await bot.load_extension("commands.generic")
        await bot.start(config.token)


asyncio.run(main())
