from .game_commands import GameCommands

async def setup(bot):
    await bot.add_cog(GameCommands(bot))
