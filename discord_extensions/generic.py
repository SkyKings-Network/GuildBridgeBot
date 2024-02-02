import discord
from discord.ext import commands
from core.config import discord as config


class Generic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(
            title="Bridge Bot | Help Commands",
            description="``< >`` = Required arguments\n``[ ]`` = Optional arguments",
            colour=0x1ABC9C, timestamp=ctx.message.created_at
        )
        embed.add_field(
            name="Discord Commands",
            value=f"``{config.prefix}invite <username>``: Invites the user to the guild\n"
                  f"``{config.prefix}promote <username>``: Promotes the given user\n"
                  f"``{config.prefix}demote <username>``: Demotes the given user\n"
                  f"``{config.prefix}setrank <username> <rank>``: Sets the given user to a specific rank\n"
                  f"``{config.prefix}kick <username> [reason]``: Kicks the given user\n"
                  f"``{config.prefix}notifications``: Toggles join / leave notifications\n"
                  f"``{config.prefix}online``: Shows the online members\n"
                  f"``{config.prefix}override <command>``: Forces the bot to use a given command\n"
                  f"``{config.prefix}toggleaccept``: Toggles auto accepting members joining the guild\n"
                  f"``{config.prefix}mute <username> <time>`` - Mutes the user for a specific time\n"
                  f"``{config.prefix}unmute <username>`` - Unmutes the user",
            inline=False
        )
        embed.add_field(
            name="Info",
            value=f"Prefix: ``{config.prefix}``\n"
                  f"Guild Channel: <#{config.channel}>\n"
                  f"Officer Channel: <#{config.officerChannel}>\n"
                  f"Command Role: <@&{config.commandRole}>\n"
                  f"Override Role: <@&{config.overrideRole}>\n"
                  f"Version: ``1.0``",
            inline=False
        )
        embed.set_footer(text=f"Made by SkyKings")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Generic(bot))
