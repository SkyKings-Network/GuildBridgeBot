import asyncio
import os
import subprocess
import sys

try:
    from core.discord_bot import DiscordBridgeBot
    from core.config import DiscordConfig, SettingsConfig
except ModuleNotFoundError as e:
    missing_module = str(e).split("'")[1]
    print(f"Module {missing_module} not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", missing_module])
    print(f"Module {missing_module} installed. Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)

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
