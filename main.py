from core.discord_bot import DiscordBridgeBot
import asyncio
from core.config import DiscordConfig, SettingsConfig

bot = DiscordBridgeBot()


async def main():
    async with bot:
        await bot.load_extension("discord_extensions.admin")
        await bot.load_extension("discord_extensions.bridge")
        await bot.load_extension("discord_extensions.generic")
        if SettingsConfig.extensions:
            print(f"Ext > Loading {len(SettingsConfig.extensions)} extensions...")
            for extension in SettingsConfig.extensions:
                await bot.load_extension(extension, package="extensions" if extension.startswith(".") else None)
                print(f"Ext > {extension} loaded!")
            print("Ext > Extensions loaded!")
        await bot.start(DiscordConfig.token)


asyncio.run(main())
