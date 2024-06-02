from core.discord_bot import DiscordBridgeBot
import asyncio
from core.config import DiscordConfig, SettingsConfig

bot = DiscordBridgeBot()


async def main():
    async with bot:
        await bot.load_extension("discord_extensions.admin")
        await bot.load_extension("discord_extensions.bridge")
        await bot.load_extension("discord_extensions.generic")
        print(SettingsConfig.extensions, type(SettingsConfig.extensions))
        for extension in SettingsConfig.extensions:
            await bot.load_extension(extension)
        print("Extensions loaded!")
        await bot.start(DiscordConfig.token)


asyncio.run(main())
