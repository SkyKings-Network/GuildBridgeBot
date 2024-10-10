import asyncio

import discord


async def send_temp_message(ctx, embed):
        message = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await message.delete()
        except discord.errors.NotFound:
            pass
